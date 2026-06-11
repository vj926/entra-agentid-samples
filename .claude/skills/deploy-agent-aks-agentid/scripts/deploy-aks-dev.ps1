# One-shot orchestrator. Dot-source your deploy-vars.ps1 first, or set
# $env:VARS_FILE to its path and this script will dot-source it for you.
#
#   cp .claude/skills/deploy-agent-aks-agentid/scripts/deploy-vars.ps1.template ~/deploy-vars.ps1
#   # Edit ~/deploy-vars.ps1 — fill in TENANT_ID, SUBSCRIPTION_ID, etc.
#   $env:VARS_FILE = "$HOME/deploy-vars.ps1"
#   pwsh -NoProfile -File .claude/skills/deploy-agent-aks-agentid/scripts/deploy-aks-dev.ps1
#
# Prerequisite: Entra Agent ID Blueprint + Agent already exist.
# Set BLUEPRINT_APP_ID and AGENT_CLIENT_ID in deploy-vars.ps1.
# CLIENT_SPA_APP_ID is optional (autonomous path doesn't need it).
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

# Validate required vars.
foreach ($v in @('TENANT_ID','SUBSCRIPTION_ID','RG','LOCATION','AKS_NAME','ACR_NAME',
                  'NODE_COUNT','NODE_VM_SIZE','BLUEPRINT_APP_ID','AGENT_CLIENT_ID','OLLAMA_MODEL')) {
    if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($v))) {
        throw "`$$v is unset. Edit $varsFile."
    }
}
if (-not $env:CLIENT_SPA_APP_ID)      { $env:CLIENT_SPA_APP_ID = "not-used" }
if (-not $env:SUBSCRIPTION_TENANT_ID) { $env:SUBSCRIPTION_TENANT_ID = $env:TENANT_ID }

Write-Host "============================================================"
Write-Host " AKS deploy plan"
if ($env:SUBSCRIPTION_TENANT_ID -ne $env:TENANT_ID) {
    Write-Host "   *** CROSS-TENANT DEPLOY ***"
    Write-Host "   Entra tenant (Blueprint/Agent) : $env:TENANT_ID"
    Write-Host "   Azure sub tenant (AKS/ACR)     : $env:SUBSCRIPTION_TENANT_ID"
    Write-Host "   Subscription                   : $env:SUBSCRIPTION_ID"
} else {
    Write-Host "   Tenant/Sub : $env:TENANT_ID / $env:SUBSCRIPTION_ID"
}
Write-Host "   RG/Location: $env:RG / $env:LOCATION"
Write-Host "   AKS / ACR  : $env:AKS_NAME / $env:ACR_NAME"
Write-Host "   Nodes      : $env:NODE_COUNT x $env:NODE_VM_SIZE"
Write-Host "   Model      : $env:OLLAMA_MODEL"
Write-Host "============================================================"

# Step 01: Create RG + ACR + AKS cluster (writes OIDC_ISSUER back to $varsFile).
& pwsh -NoProfile -File (Join-Path $scriptDir "01-create-aks.ps1")
if ($LASTEXITCODE -ne 0) { throw "01-create-aks.ps1 failed." }

# Re-source to pick up OIDC_ISSUER written by step 01.
. $varsFile

# Step 02: Build and push container images.
& pwsh -NoProfile -File (Join-Path $scriptDir "02-build-and-push.ps1")
if ($LASTEXITCODE -ne 0) { throw "02-build-and-push.ps1 failed." }

# Step 03: Federate the KSA to the Blueprint app.
$ficName = $env:FIC_NAME ? $env:FIC_NAME : "aks-agent-sa"
& pwsh -NoProfile -File (Join-Path $scriptDir "03-federate-blueprint.ps1") `
    -TenantId       $env:TENANT_ID `
    -BlueprintAppId $env:BLUEPRINT_APP_ID `
    -OidcIssuerUrl  $env:OIDC_ISSUER `
    -FicName        $ficName
if ($LASTEXITCODE -ne 0) { throw "03-federate-blueprint.ps1 failed." }

# Step 04: Render manifests and apply to AKS.
& pwsh -NoProfile -File (Join-Path $scriptDir "04-apply-manifests.ps1")
if ($LASTEXITCODE -ne 0) { throw "04-apply-manifests.ps1 failed." }

Write-Host ""
Write-Host "============================================================"
$lbIp = (kubectl get svc -n agentid llm-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null).Trim()
Write-Host " Done. Agent UI:  http://$($lbIp ? $lbIp : '<pending>')"
Write-Host ""
Write-Host " Verify:"
Write-Host "   kubectl get pods -n agentid"
Write-Host "   kubectl logs -n agentid -l app=llm-agent -c sidecar --tail=50"
Write-Host ""
Write-Host " Autonomous (app-only) path is ready as-is — no Entra config needed."
Write-Host " Open the URL above and chat; the agent acquires its own Agent Identity"
Write-Host " token via the Blueprint FIC."
Write-Host ""
Write-Host " For user On-Behalf-Of (sign-in) mode (REQUIRED for the 'Sign In' button):"
Write-Host "   1) Register SPA redirect URIs (localhost:8080 for OBO + LB-IP for autonomous):"
Write-Host "        `$env:APP_FQDN = '$lbIp'"
Write-Host "        pwsh -NoProfile -File `"$scriptDir\add-spa-redirect-uri.ps1`""
Write-Host "   2) Grant Agent -> Graph delegated User.Read admin consent:"
Write-Host "        pwsh -NoProfile -File `"$scriptDir\grant-agent-obo-consent.ps1`" ``"
Write-Host "          -AgentAppId `"$env:AGENT_CLIENT_ID`" -TenantId `"$env:TENANT_ID`""
Write-Host "   3) Port-forward to localhost (PKCE needs a secure context — raw HTTP IPs"
Write-Host "      are not secure-context; loopback is exempt):"
Write-Host "        pwsh -NoProfile -File `"$scriptDir\port-forward.ps1`""
Write-Host "      Then open http://localhost:8080 and click Sign In."
Write-Host "============================================================"
