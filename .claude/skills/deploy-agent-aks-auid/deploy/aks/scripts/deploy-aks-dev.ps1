# One-shot orchestrator. Dot-source your deploy-vars.ps1 first, or set
# $env:VARS_FILE to its path and this script will dot-source it for you.
#
#   cp deploy/aks/scripts/deploy-vars.ps1.template ~/deploy-vars-auid.ps1
#   # Edit ~/deploy-vars-auid.ps1
#   $env:VARS_FILE = "$HOME/deploy-vars-auid.ps1"
#   pwsh -NoProfile -File deploy/aks/scripts/deploy-aks-dev.ps1
#
# Prerequisites:
#  - Blueprint + Agent Identity already created (use the entra-agent-id-setup
#    workflow). BLUEPRINT_APP_ID and AGENT_IDENTITY_APP_ID set in deploy-vars.
#  - Agentic User provisioned (../../../scripts/01-provision-agentic-user.ps1).
#  - Weather Agent app registered with exposed scope, Agent Identity granted
#    admin consent for it (../../../scripts/04-register-weather-app.ps1).
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = $PSScriptRoot
$varsFile  = if ($env:VARS_FILE) { $env:VARS_FILE } else {
    throw "VARS_FILE not set. Point `$env:VARS_FILE to your deploy-vars.ps1 and re-run."
}
if (-not (Test-Path $varsFile)) {
    throw "Vars file '$varsFile' not found. Copy deploy-vars.ps1.template, fill it in, and set `$env:VARS_FILE."
}
. $varsFile

foreach ($v in @('TENANT_ID','SUBSCRIPTION_ID','RG','LOCATION','AKS_NAME','ACR_NAME',
                  'NODE_COUNT','NODE_VM_SIZE','BLUEPRINT_APP_ID','AGENT_IDENTITY_APP_ID',
                  'AGENT_USER_UPN','WEATHER_AGENT_APP_ID','WEATHER_AGENT_APP_ID_URI')) {
    if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($v))) {
        throw "`$$v is unset. Edit $varsFile."
    }
}
if (-not $env:SUBSCRIPTION_TENANT_ID) { $env:SUBSCRIPTION_TENANT_ID = $env:TENANT_ID }

Write-Host "============================================================"
Write-Host " AUID-on-AKS deploy plan"
if ($env:SUBSCRIPTION_TENANT_ID -ne $env:TENANT_ID) {
    Write-Host "   *** CROSS-TENANT DEPLOY ***"
    Write-Host "   Entra tenant : $env:TENANT_ID"
    Write-Host "   Sub tenant   : $env:SUBSCRIPTION_TENANT_ID"
}
Write-Host "   Subscription : $env:SUBSCRIPTION_ID"
Write-Host "   RG/Location  : $env:RG / $env:LOCATION"
Write-Host "   AKS / ACR    : $env:AKS_NAME / $env:ACR_NAME"
Write-Host "   Blueprint    : $env:BLUEPRINT_APP_ID"
Write-Host "   Agent ID     : $env:AGENT_IDENTITY_APP_ID"
Write-Host "   Agent User   : $env:AGENT_USER_UPN"
Write-Host "   Weather App  : $env:WEATHER_AGENT_APP_ID ($env:WEATHER_AGENT_APP_ID_URI)"
Write-Host "============================================================"

# Step 01: Create RG + ACR + AKS (writes OIDC_ISSUER back to varsFile).
& pwsh -NoProfile -File (Join-Path $scriptDir "01-create-aks.ps1")
if ($LASTEXITCODE -ne 0) { throw "01-create-aks.ps1 failed." }

# Re-source to pick up OIDC_ISSUER written by step 01.
. $varsFile

# Step 02: Build and push container images.
& pwsh -NoProfile -File (Join-Path $scriptDir "02-build-and-push.ps1")
if ($LASTEXITCODE -ne 0) { throw "02-build-and-push.ps1 failed." }

# Step 03: Federate the KSA to the Blueprint app.
$ficName = $env:FIC_NAME ? $env:FIC_NAME : "aks-backend-sa"
& pwsh -NoProfile -File (Join-Path $scriptDir "03-federate-blueprint.ps1") `
    -TenantId       $env:TENANT_ID `
    -BlueprintAppId $env:BLUEPRINT_APP_ID `
    -OidcIssuerUrl  $env:OIDC_ISSUER `
    -FicName        $ficName
if ($LASTEXITCODE -ne 0) { throw "03-federate-blueprint.ps1 failed." }

# Step 04: Render manifests and apply to AKS.
& pwsh -NoProfile -File (Join-Path $scriptDir "04-apply-manifests.ps1")
if ($LASTEXITCODE -ne 0) { throw "04-apply-manifests.ps1 failed." }

$lbIp = (kubectl get svc -n auid ui -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null).Trim()
Write-Host ""
Write-Host "============================================================"
Write-Host " Done. AUID demo UI: http://$($lbIp ? $lbIp : '<pending>')/"
Write-Host ""
Write-Host " Verify:"
Write-Host "   kubectl get pods -n auid"
Write-Host "   kubectl logs -n auid -l app=backend -c sidecar --tail=50"
Write-Host "   kubectl logs -n auid -l app=backend -c backend --tail=50"
Write-Host ""
Write-Host " Smoke-test the AUID acquisition from inside the cluster:"
Write-Host "   kubectl exec -n auid deploy/backend -c backend -- ``"
Write-Host "     curl -s -X POST http://localhost:8080/api/step/03-auid-token | Select-Object -First 600"
Write-Host "============================================================"
