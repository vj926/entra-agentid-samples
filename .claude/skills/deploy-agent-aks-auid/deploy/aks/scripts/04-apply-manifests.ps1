# Render manifests via PowerShell string substitution and apply.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

foreach ($v in @('TENANT_ID','BLUEPRINT_APP_ID','AGENT_IDENTITY_APP_ID','AGENT_USER_UPN',
                  'WEATHER_AGENT_APP_ID','WEATHER_AGENT_APP_ID_URI','ACR_NAME')) {
    if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($v))) {
        throw "Missing `$$v — source your deploy-vars.ps1 first."
    }
}
if (-not $env:AGENT_USER_OBJECT_ID) { $env:AGENT_USER_OBJECT_ID = "" }

$scriptDir    = $PSScriptRoot
$manifestsDir = [System.IO.Path]::GetFullPath((Join-Path $scriptDir ".." "manifests"))
$outDir       = Join-Path ([System.IO.Path]::GetTempPath()) "auid-aks-rendered"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# Substitution map — longer names before shorter prefixes to avoid partial replacements.
$subs = [ordered]@{
    '$AGENT_IDENTITY_APP_ID'   = $env:AGENT_IDENTITY_APP_ID
    '$WEATHER_AGENT_APP_ID_URI'= $env:WEATHER_AGENT_APP_ID_URI
    '$WEATHER_AGENT_APP_ID'    = $env:WEATHER_AGENT_APP_ID
    '$AGENT_USER_OBJECT_ID'    = $env:AGENT_USER_OBJECT_ID
    '$BLUEPRINT_APP_ID'        = $env:BLUEPRINT_APP_ID
    '$AGENT_USER_UPN'          = $env:AGENT_USER_UPN
    '$TENANT_ID'               = $env:TENANT_ID
    '$ACR_NAME'                = $env:ACR_NAME
}

Get-ChildItem $manifestsDir -Filter "*.yaml" | Sort-Object Name | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    foreach ($kv in $subs.GetEnumerator()) {
        $content = $content.Replace($kv.Key, $kv.Value)
    }
    Set-Content -Path (Join-Path $outDir $_.Name) -Value $content -NoNewline
}

kubectl apply -f (Join-Path $outDir "00-namespace.yaml")
kubectl apply -f (Join-Path $outDir "10-serviceaccount.yaml")
kubectl apply -f (Join-Path $outDir "20-weather-agent.yaml")
kubectl apply -f (Join-Path $outDir "30-ui.yaml")
kubectl apply -f (Join-Path $outDir "40-backend.yaml")

Write-Host ""
Write-Host "Waiting for rollouts..."
kubectl -n auid rollout status deploy/weather-agent --timeout=180s
kubectl -n auid rollout status deploy/backend       --timeout=180s
kubectl -n auid rollout status deploy/ui            --timeout=120s

Write-Host ""
Write-Host "Waiting for LoadBalancer IP..."
$ip = $null
for ($i = 0; $i -lt 60; $i++) {
    $ip = (kubectl -n auid get svc ui -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null).Trim()
    if ($ip) { break }
    Start-Sleep 5
}
Write-Host "AUID demo UI: http://$($ip ?? '<pending>')/"
