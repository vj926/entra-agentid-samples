# Render manifests with PowerShell string substitution and apply.
# Replaces envsubst: reads each *.yaml, substitutes $VAR tokens, writes to
# a temp directory, then kubectl-applies in order.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

foreach ($v in @('TENANT_ID','BLUEPRINT_APP_ID','AGENT_CLIENT_ID','ACR_NAME','OLLAMA_MODEL')) {
    if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($v))) {
        throw "Missing `$$v — source your deploy-vars.ps1 first."
    }
}

# CLIENT_SPA_APP_ID is optional. Default AKS path is autonomous (app-only) auth.
# Only set it if you also want to enable user-OBO mode in the llm-agent UI.
if (-not $env:CLIENT_SPA_APP_ID) { $env:CLIENT_SPA_APP_ID = "not-used" }

$scriptDir    = $PSScriptRoot
$manifestsDir = [System.IO.Path]::GetFullPath((Join-Path $scriptDir ".." "manifests"))
$outDir       = Join-Path ([System.IO.Path]::GetTempPath()) "agentid-aks-rendered"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# Substitution map — order matters: replace longer names before shorter prefixes.
$subs = [ordered]@{
    '$CLIENT_SPA_APP_ID'  = $env:CLIENT_SPA_APP_ID
    '$BLUEPRINT_APP_ID'   = $env:BLUEPRINT_APP_ID
    '$AGENT_CLIENT_ID'    = $env:AGENT_CLIENT_ID
    '$OLLAMA_MODEL'       = $env:OLLAMA_MODEL
    '$TENANT_ID'          = $env:TENANT_ID
    '$ACR_NAME'           = $env:ACR_NAME
}

Get-ChildItem $manifestsDir -Filter "*.yaml" | Sort-Object Name | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    foreach ($kv in $subs.GetEnumerator()) {
        $content = $content.Replace($kv.Key, $kv.Value)
    }
    $dest = Join-Path $outDir $_.Name
    Set-Content -Path $dest -Value $content -NoNewline
}

kubectl apply -f (Join-Path $outDir "00-namespace.yaml")
kubectl apply -f (Join-Path $outDir "10-serviceaccount.yaml")
kubectl apply -f (Join-Path $outDir "20-weather-api.yaml")
kubectl apply -f (Join-Path $outDir "30-ollama.yaml")
kubectl apply -f (Join-Path $outDir "40-agent.yaml")
kubectl apply -f (Join-Path $outDir "50-ingress.yaml")

Write-Host ""
Write-Host "Waiting for rollouts..."
kubectl -n agentid rollout status deploy/weather-api --timeout=180s
kubectl -n agentid rollout status deploy/ollama       --timeout=600s
kubectl -n agentid rollout status deploy/llm-agent    --timeout=180s

Write-Host ""
Write-Host "Waiting for LoadBalancer IP..."
$ip = $null
for ($i = 0; $i -lt 60; $i++) {
    $ip = (kubectl -n agentid get svc llm-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null).Trim()
    if ($ip) { break }
    Start-Sleep 5
}
Write-Host "Agent UI: http://$($ip ?? '<pending>')/"
