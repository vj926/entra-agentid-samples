# smoke-test-kind.ps1 — validate the AKS manifests on a local `kind` cluster
# without any Azure resources. Uses the ClientSecret credential source instead
# of workload identity (since kind has no Entra-trusted OIDC).
#
# Usage:
#   . ~/deploy-vars.ps1
#   $env:BLUEPRINT_CLIENT_SECRET = "<secret>"
#   pwsh -NoProfile -File smoke-test-kind.ps1
#   pwsh -NoProfile -File smoke-test-kind.ps1 --cleanup

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$cluster = "agentid-smoke"
$ns      = "agentid"

$scriptDir = $PSScriptRoot
$manifestsDir = [System.IO.Path]::GetFullPath((Join-Path $scriptDir ".." "manifests"))
$repoRoot     = [System.IO.Path]::GetFullPath((Join-Path $scriptDir ".." ".." ".." ".."))

function Find-SidecarRoot {
    $candidates = @(
        (Join-Path $repoRoot "sidecar"),
        (Join-Path $repoRoot "reference" "repo" "sidecar")
    )
    foreach ($c in $candidates) {
        $c = [System.IO.Path]::GetFullPath($c)
        if ((Test-Path (Join-Path $c "dev")) -and (Test-Path (Join-Path $c "weather-api"))) {
            return $c
        }
    }
    return $null
}

# Handle --cleanup flag.
if ($args -contains "--cleanup") {
    kind delete cluster --name $cluster 2>$null
    Write-Host "Cleanup complete."
    exit 0
}

function Fail([string]$msg) { throw "SMOKE FAIL: $msg" }
function Have([string]$tool) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail "missing tool: $tool" }
}

Have "docker"
Have "kind"
Have "kubectl"

foreach ($v in @('TENANT_ID','BLUEPRINT_APP_ID','AGENT_CLIENT_ID','CLIENT_SPA_APP_ID','OLLAMA_MODEL')) {
    if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($v))) {
        Fail "$v not set (source your deploy-vars.ps1)"
    }
}

if (-not $env:BLUEPRINT_CLIENT_SECRET) {
    Write-Host "WARN: BLUEPRINT_CLIENT_SECRET unset — sidecar won't acquire tokens,"
    Write-Host "      but the rest of the wiring will still be validated."
    $env:BLUEPRINT_CLIENT_SECRET = "placeholder-for-smoke-only"
}

$sidecarRoot = Find-SidecarRoot
if (-not $sidecarRoot) { Fail "could not locate sidecar/{dev,weather-api}" }

Write-Host "==> [1/7] Create kind cluster"
$existingClusters = kind get clusters 2>$null
if ($existingClusters -notcontains $cluster) {
    kind create cluster --name $cluster --wait 60s
}
kubectl cluster-info --context "kind-$cluster"

$outDir = Join-Path ([System.IO.Path]::GetTempPath()) "agentid-smoke-rendered"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "==> [2/7] Build images locally"
$buildLog = Join-Path ([System.IO.Path]::GetTempPath()) "kind-build-agent.log"
$proc = Start-Process docker -ArgumentList @("build","-t","agent-id-dev/llm-agent:smoke",(Join-Path $sidecarRoot "dev")) `
    -RedirectStandardOutput $buildLog -RedirectStandardError $buildLog -Wait -PassThru -NoNewWindow
if ($proc.ExitCode -ne 0) {
    Get-Content $buildLog | Select-Object -Last 50
    Fail "image build (llm-agent)"
}

$buildLog2 = Join-Path ([System.IO.Path]::GetTempPath()) "kind-build-weather.log"
$proc2 = Start-Process docker -ArgumentList @("build","-t","agent-id-dev/weather-api:smoke",(Join-Path $sidecarRoot "weather-api")) `
    -RedirectStandardOutput $buildLog2 -RedirectStandardError $buildLog2 -Wait -PassThru -NoNewWindow
if ($proc2.ExitCode -ne 0) {
    Get-Content $buildLog2 | Select-Object -Last 50
    Fail "image build (weather-api)"
}

Write-Host "==> [3/7] Load images into kind"
kind load docker-image agent-id-dev/llm-agent:smoke   --name $cluster
kind load docker-image agent-id-dev/weather-api:smoke --name $cluster

Write-Host "==> [4/7] Render manifests (smoke overlay)"
$acrNameProd = $env:ACR_NAME ? $env:ACR_NAME : "acr-placeholder"
$subs = [ordered]@{
    '$CLIENT_SPA_APP_ID'  = $env:CLIENT_SPA_APP_ID
    '$BLUEPRINT_APP_ID'   = $env:BLUEPRINT_APP_ID
    '$AGENT_CLIENT_ID'    = $env:AGENT_CLIENT_ID
    '$OLLAMA_MODEL'       = $env:OLLAMA_MODEL
    '$TENANT_ID'          = $env:TENANT_ID
    '$ACR_NAME'           = $acrNameProd
}

Get-ChildItem $manifestsDir -Filter "*.yaml" | Sort-Object Name | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    foreach ($kv in $subs.GetEnumerator()) {
        $content = $content.Replace($kv.Key, $kv.Value)
    }
    # Rewrite ACR image refs to the locally-loaded smoke tags.
    $content = $content -replace [regex]::Escape("${acrNameProd}.azurecr.io/agent-id-dev/llm-agent:1.0.0"),   "agent-id-dev/llm-agent:smoke"
    $content = $content -replace [regex]::Escape("${acrNameProd}.azurecr.io/agent-id-dev/weather-api:1.0.0"), "agent-id-dev/weather-api:smoke"
    Set-Content -Path (Join-Path $outDir $_.Name) -Value $content -NoNewline
}

# Patch 40-agent.yaml: strip workload-identity bits, inject ClientSecret credential source.
$agentFile = Join-Path $outDir "40-agent.yaml"
$saFile    = Join-Path $outDir "10-serviceaccount.yaml"

$agentContent = Get-Content $agentFile -Raw
$agentContent = $agentContent.Replace('azure.workload.identity/use: "true"', '# (workload-identity disabled in smoke test)')
$agentContent = [regex]::Replace(
    $agentContent,
    '- \{ name: AzureAd__ClientCredentials__0__SourceType,[^}]*\}\s*\r?\n\s*- \{ name: AzureAd__ClientCredentials__0__SignedAssertionFileDiskPath,[^}]*\}',
    "- { name: AzureAd__ClientCredentials__0__SourceType, value: `"ClientSecret`" }`n            - name: AzureAd__ClientCredentials__0__ClientSecret`n              valueFrom:`n                secretKeyRef: { name: blueprint-secret, key: client-secret }"
)
Set-Content -Path $agentFile -Value $agentContent -NoNewline

$saContent = Get-Content $saFile -Raw
$saContent = [regex]::Replace($saContent, '\r?\n\s+azure\.workload\.identity/[^\r\n]*', '')
Set-Content -Path $saFile -Value $saContent -NoNewline

Write-Host "==> [5/7] Apply"
kubectl apply -f (Join-Path $outDir "00-namespace.yaml")
kubectl -n $ns create secret generic blueprint-secret `
    --from-literal="client-secret=$env:BLUEPRINT_CLIENT_SECRET" `
    --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f $saFile
kubectl apply -f (Join-Path $outDir "20-weather-api.yaml")
kubectl apply -f (Join-Path $outDir "30-ollama.yaml")
kubectl apply -f $agentFile
# Skip 50-ingress.yaml: kind doesn't have a cloud LB. Use port-forward instead.

Write-Host "==> [6/7] Wait for rollouts"
kubectl -n $ns rollout status deploy/weather-api --timeout=180s
if ($LASTEXITCODE -ne 0) { Fail "weather-api rollout" }
kubectl -n $ns rollout status deploy/ollama --timeout=600s
if ($LASTEXITCODE -ne 0) { Fail "ollama rollout (model pull is slow on first run)" }
kubectl -n $ns rollout status deploy/llm-agent --timeout=180s
if ($LASTEXITCODE -ne 0) { Fail "llm-agent rollout" }

Write-Host "==> [7/7] Hit /status"
$pfJob = Start-Job { kubectl -n agentid port-forward deploy/llm-agent 3000:3000 }
try {
    Start-Sleep 3
    $status = (Invoke-RestMethod -Uri "http://127.0.0.1:3000/status" -ErrorAction SilentlyContinue) | ConvertTo-Json -Compress
    if (-not $status) { Fail "agent /status returned empty" }
    Write-Host "  /status -> $status"
    if ($status -notmatch "ollama_available") { Fail "agent /status did not include ollama_available; got: $status" }
    if ($status -notmatch '"ollama_available":true') { Fail "ollama_available is not true" }
} finally {
    Stop-Job $pfJob -ErrorAction SilentlyContinue
    Remove-Job $pfJob -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "SMOKE PASS — manifests apply, all rollouts succeed, agent reaches Ollama."
Write-Host "Run 'pwsh $PSCommandPath --cleanup' to tear down the kind cluster."
