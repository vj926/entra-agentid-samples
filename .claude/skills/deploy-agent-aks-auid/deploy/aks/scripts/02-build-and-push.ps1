# Build and push backend, weather-agent, and ui images via `az acr build`.
# No local Docker required.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $env:ACR_NAME) { throw "ACR_NAME is required. Source your deploy-vars.ps1 first." }

$scriptDir = $PSScriptRoot
$repoRoot  = [System.IO.Path]::GetFullPath((Join-Path $scriptDir ".." ".." ".."))

Write-Host "[1/3] backend  ($repoRoot/backend)"
& az acr build --registry $env:ACR_NAME `
    --image auid-aks/backend:1.0.0 `
    --platform linux/amd64 `
    (Join-Path $repoRoot "backend")

Write-Host "[2/3] weather-agent  ($repoRoot/weather-agent)"
& az acr build --registry $env:ACR_NAME `
    --image auid-aks/weather-agent:1.0.0 `
    --platform linux/amd64 `
    (Join-Path $repoRoot "weather-agent")

Write-Host "[3/3] ui  ($repoRoot/ui)"
& az acr build --registry $env:ACR_NAME `
    --image auid-aks/ui:1.0.0 `
    --platform linux/amd64 `
    (Join-Path $repoRoot "ui")
