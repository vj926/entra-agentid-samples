# Build & push llm-agent and weather-api to ACR using `az acr build`
# (no local Docker required). Ollama uses the upstream image as-is — the
# 30-ollama.yaml manifest pulls the model into a PVC via initContainer.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $env:ACR_NAME) { throw "ACR_NAME is required. Source your deploy-vars.ps1 first." }

$scriptDir = $PSScriptRoot

# Locate the sidecar source dirs (`dev/` and `weather-api/`). Two supported layouts:
#   A) Upstream repo layout: <repo>/sidecar/{dev,weather-api,aks}
#   B) Reference-clone layout: <ws>/reference/repo/sidecar/{dev,weather-api}
function Find-SidecarRoot {
    $candidates = @(
        [System.IO.Path]::GetFullPath((Join-Path $scriptDir "../../../../sidecar")),
        [System.IO.Path]::GetFullPath((Join-Path $scriptDir "../../../sidecar")),
        [System.IO.Path]::GetFullPath((Join-Path $scriptDir "../../../reference/repo/sidecar"))
    )
    foreach ($c in $candidates) {
        if ((Test-Path (Join-Path $c "dev")) -and (Test-Path (Join-Path $c "weather-api"))) {
            return $c
        }
    }
    return $null
}

$sidecarRoot = Find-SidecarRoot
if (-not $sidecarRoot) {
    throw "ERROR: could not locate sidecar/{dev,weather-api}. Tried upstream and reference layouts."
}

Write-Host "[1/2] llm-agent  (source: $sidecarRoot/dev)"
& az acr build --registry $env:ACR_NAME `
    --image agent-id-dev/llm-agent:1.0.0 `
    --platform linux/amd64 `
    (Join-Path $sidecarRoot "dev")

Write-Host "[2/2] weather-api  (source: $sidecarRoot/weather-api)"
& az acr build --registry $env:ACR_NAME `
    --image agent-id-dev/weather-api:1.0.0 `
    --platform linux/amd64 `
    (Join-Path $sidecarRoot "weather-api")
