# teardown-aks-dev.ps1 — complete teardown of the deploy-agent-aks-agentid skill.
#
# Safe by default: -DryRun is $true, -DeleteEntra is $false.
#
# Usage:
#   pwsh -NoProfile -File teardown-aks-dev.ps1                              # dry-run
#   pwsh -NoProfile -File teardown-aks-dev.ps1 -DryRun:$false               # real, RG + FIC
#   pwsh -NoProfile -File teardown-aks-dev.ps1 -DryRun:$false -DeleteEntra  # full
#   pwsh -NoProfile -File teardown-aks-dev.ps1 -FicOnly                     # FIC only, no RG
#
# What this script removes (matching exactly what deploy-agent-aks-agentid creates):
#   - k8s `agentid` namespace (graceful cleanup before RG deletion)
#   - SPA redirect URIs added by add-spa-redirect-uri.ps1
#   - OAuth consent grants on the Agent SP
#   - Federated Identity Credential on the Blueprint app
#   - Resource group (AKS cluster + ACR + LB + PVCs)
#   - Entra apps (opt-in): Client SPA, Agent Identity, Blueprint
#
# Exit codes:
#   0 — completed (or dry-run completed)
#   1 — missing required vars / preflight failed
#   2 — user aborted at confirmation prompt
#   3 — partial failure

param(
    [string]  $VarsFile     = "",
    [switch]  $DryRun       = $true,
    [switch]  $DeleteEntra  = $false,
    [switch]  $FicOnly      = $false
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Resolve vars file.
if (-not $VarsFile) {
    $VarsFile = if ($env:VARS_FILE) { $env:VARS_FILE } else {
        Join-Path ([System.IO.Path]::GetTempPath()) "deploy-vars.ps1"
    }
}
if (-not (Test-Path $VarsFile)) {
    Write-Error "ERROR: '$VarsFile' not found. Re-export at minimum SUBSCRIPTION_ID, RG, TENANT_ID, BLUEPRINT_APP_ID."
    exit 1
}
. $VarsFile

if (-not $env:SUBSCRIPTION_TENANT_ID) { $env:SUBSCRIPTION_TENANT_ID = $env:TENANT_ID }
if (-not $env:FIC_NAME)               { $env:FIC_NAME = "aks-agent-sa" }

# Validate required vars.
if (-not $env:TENANT_ID)        { Write-Error "TENANT_ID required in $VarsFile"; exit 1 }
if (-not $env:BLUEPRINT_APP_ID) { Write-Error "BLUEPRINT_APP_ID required in $VarsFile"; exit 1 }
if (-not $FicOnly) {
    if (-not $env:SUBSCRIPTION_ID) { Write-Error "SUBSCRIPTION_ID required in $VarsFile"; exit 1 }
    if (-not $env:RG)              { Write-Error "RG required in $VarsFile"; exit 1 }
}

function Invoke-Step([string]$description, [scriptblock]$action) {
    if ($DryRun) {
        Write-Host "DRY-RUN: $description"
    } else {
        Write-Host "+ $description"
        & $action
    }
}

function Confirm-Step([string]$prompt) {
    if ($DryRun) {
        Write-Host "DRY-RUN: would prompt '$prompt' — assuming yes"
        return $true
    }
    $ans = Read-Host "$prompt [y/N]"
    return $ans -eq 'y' -or $ans -eq 'Y'
}

# ----------------------------------------------------------------------
# Print teardown plan.
# ----------------------------------------------------------------------
Write-Host "============================================================"
Write-Host "Teardown plan (AKS / Entra Agent ID)"
if (-not $FicOnly) {
    Write-Host "  Subscription tenant: $env:SUBSCRIPTION_TENANT_ID"
    Write-Host "  Subscription:        $env:SUBSCRIPTION_ID"
    Write-Host "  Resource group:      $env:RG               (WILL be deleted)"
}
Write-Host "  Entra tenant:        $env:TENANT_ID"
Write-Host "  Blueprint app:       $env:BLUEPRINT_APP_ID"
Write-Host "    └─ FIC to remove:  $env:FIC_NAME"
if (-not $FicOnly) {
    Write-Host "  Delete Entra apps:   $DeleteEntra"
    Write-Host "  Namespace cleanup:   agentid (if cluster reachable)"
    if ($env:CLIENT_SPA_APP_ID) {
        Write-Host "  SPA redirect URIs:   will remove port-forward + LB URIs"
    }
}
Write-Host "  Dry run:             $DryRun"
Write-Host "  FIC-only mode:       $FicOnly"
Write-Host "============================================================"
if (-not (Confirm-Step "Proceed?")) { Write-Host "Aborted."; exit 2 }

Import-Module Microsoft.Graph.Authentication -ErrorAction Stop

# ----------------------------------------------------------------------
# FIC-only fast path.
# ----------------------------------------------------------------------
if ($FicOnly) {
    Write-Host ""
    Write-Host "Step F — Delete FIC '$env:FIC_NAME' from Blueprint $env:BLUEPRINT_APP_ID"
    Connect-MgGraph -TenantId $env:TENANT_ID -Scopes "Application.ReadWrite.OwnedBy" -NoWelcome | Out-Null
    try {
        $bpApp = Invoke-MgGraphRequest -Method GET `
            -Uri "https://graph.microsoft.com/v1.0/applications(appId='$($env:BLUEPRINT_APP_ID)')?`$select=id"
        $fics = Invoke-MgGraphRequest -Method GET `
            -Uri "https://graph.microsoft.com/v1.0/applications/$($bpApp.id)/federatedIdentityCredentials"
        $fic = $fics.value | Where-Object { $_.name -eq $env:FIC_NAME } | Select-Object -First 1
        if (-not $fic) {
            Write-Host "  (FIC '$env:FIC_NAME' not present — nothing to do)"
            exit 0
        }
        Invoke-Step "DELETE FIC $($fic.id) ('$env:FIC_NAME') from Blueprint $env:BLUEPRINT_APP_ID" {
            Invoke-MgGraphRequest -Method DELETE `
                -Uri "https://graph.microsoft.com/v1.0/applications/$($bpApp.id)/federatedIdentityCredentials/$($fic.id)"
        }
        Write-Host "  FIC removed."
    } catch {
        if ($_.Exception.Message -match '404|Request_ResourceNotFound|NotFound') {
            Write-Host "  (Blueprint app not found — nothing to do)"
        } else { throw }
    }
    exit 0
}

# ----------------------------------------------------------------------
# Step 1: Remove SPA redirect URIs (added by add-spa-redirect-uri.ps1).
# ----------------------------------------------------------------------
if ($env:CLIENT_SPA_APP_ID) {
    Write-Host ""
    Write-Host "Step 1 — Remove SPA redirect URIs from Client SPA ($env:CLIENT_SPA_APP_ID)"
    try {
        Connect-MgGraph -TenantId $env:TENANT_ID -Scopes "Application.ReadWrite.OwnedBy" -NoWelcome | Out-Null
        $app = Invoke-MgGraphRequest -Method GET `
            -Uri "https://graph.microsoft.com/v1.0/applications(appId='$($env:CLIENT_SPA_APP_ID)')?`$select=id,spa"
        $currentUris = if ($app.spa -and $app.spa.redirectUris) { @($app.spa.redirectUris) } else { @() }

        # Build the set of URIs that add-spa-redirect-uri.ps1 would have registered.
        $portForwardUri = $env:PORT_FORWARD_URI ? $env:PORT_FORWARD_URI : "http://localhost:8080/"
        $appFqdn        = $env:APP_FQDN ?? ""
        $redirectScheme = $env:REDIRECT_SCHEME ? $env:REDIRECT_SCHEME : "http"
        $fqdnUri        = if ($appFqdn) { "${redirectScheme}://${appFqdn}/" } else { "" }
        $toRemove = @($portForwardUri, $fqdnUri) | Where-Object { $_ -and ($_ -in $currentUris) }

        if (-not $toRemove) {
            Write-Host "  (no matching redirect URIs found — already clean)"
        } else {
            $remaining = $currentUris | Where-Object { $_ -notin $toRemove }
            Invoke-Step "PATCH spa.redirectUris on $env:CLIENT_SPA_APP_ID (remove: $($toRemove -join ', '))" {
                $body = @{ spa = @{ redirectUris = @($remaining) } } | ConvertTo-Json -Depth 5
                Invoke-MgGraphRequest -Method PATCH `
                    -Uri "https://graph.microsoft.com/v1.0/applications/$($app.id)" `
                    -Body $body -ContentType "application/json"
            }
            Write-Host "  Removed: $($toRemove -join ', ')"
        }
    } catch {
        if ($_.Exception.Message -match '404|Request_ResourceNotFound|NotFound') {
            Write-Host "  (Client SPA app not found — skipping)"
        } else {
            Write-Host "  WARN: $($_.Exception.Message) — continuing"
        }
    }
} else {
    Write-Host ""
    Write-Host "Step 1 — Skipping SPA redirect URI cleanup (CLIENT_SPA_APP_ID not set)"
}

# ----------------------------------------------------------------------
# Step 2: Revoke OAuth consent grants on Agent SP.
# ----------------------------------------------------------------------
if ($env:AGENT_CLIENT_ID) {
    Write-Host ""
    Write-Host "Step 2 — Revoke OAuth consent grants on Agent SP ($env:AGENT_CLIENT_ID)"
    try {
        Connect-MgGraph -TenantId $env:TENANT_ID -Scopes "DelegatedPermissionGrant.ReadWrite.All","Application.Read.All" -NoWelcome | Out-Null
        $agentSp = Invoke-MgGraphRequest -Method GET `
            -Uri "https://graph.microsoft.com/v1.0/servicePrincipals(appId='$($env:AGENT_CLIENT_ID)')?`$select=id" `
            -ErrorAction SilentlyContinue
        if ($agentSp) {
            $grants = (Invoke-MgGraphRequest -Method GET `
                -Uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?`$filter=clientId eq '$($agentSp.id)'").value
            if ($grants -and $grants.Count -gt 0) {
                foreach ($g in $grants) {
                    Invoke-Step "DELETE oauth2PermissionGrant $($g.id)" {
                        Invoke-MgGraphRequest -Method DELETE `
                            -Uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants/$($g.id)"
                    }
                }
            } else {
                Write-Host "  (no grants found)"
            }
        } else {
            Write-Host "  (Agent SP not found — skipping)"
        }
    } catch {
        Write-Host "  WARN: $($_.Exception.Message) — continuing"
    }
} else {
    Write-Host ""
    Write-Host "Step 2 — Skipping OAuth grant revocation (AGENT_CLIENT_ID not set)"
}

# ----------------------------------------------------------------------
# Step 3: Delete FIC on Blueprint.
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "Step 3 — Delete FIC '$env:FIC_NAME' on Blueprint $env:BLUEPRINT_APP_ID"
try {
    Connect-MgGraph -TenantId $env:TENANT_ID -Scopes "Application.ReadWrite.OwnedBy" -NoWelcome | Out-Null
    $bpApp = Invoke-MgGraphRequest -Method GET `
        -Uri "https://graph.microsoft.com/v1.0/applications(appId='$($env:BLUEPRINT_APP_ID)')?`$select=id"
    $fics = Invoke-MgGraphRequest -Method GET `
        -Uri "https://graph.microsoft.com/v1.0/applications/$($bpApp.id)/federatedIdentityCredentials"
    $fic = $fics.value | Where-Object { $_.name -eq $env:FIC_NAME } | Select-Object -First 1
    if ($fic) {
        Invoke-Step "DELETE FIC $($fic.id) ('$env:FIC_NAME') from Blueprint $env:BLUEPRINT_APP_ID" {
            Invoke-MgGraphRequest -Method DELETE `
                -Uri "https://graph.microsoft.com/v1.0/applications/$($bpApp.id)/federatedIdentityCredentials/$($fic.id)"
        }
        Write-Host "  FIC removed."
    } else {
        Write-Host "  (FIC '$env:FIC_NAME' not present — skipping)"
    }
} catch {
    if ($_.Exception.Message -match '404|Request_ResourceNotFound|NotFound') {
        Write-Host "  (Blueprint app not found — skipping FIC delete)"
    } else {
        Write-Host "  WARN: $($_.Exception.Message) — continuing"
    }
}

# ----------------------------------------------------------------------
# Step 4: Delete the `agentid` namespace (graceful k8s cleanup).
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "Step 4 — Delete k8s namespace 'agentid' (graceful pod termination before RG delete)"
if (-not $DryRun) {
    $nsExists = kubectl get namespace agentid 2>$null
    if ($nsExists) {
        Write-Host "+ kubectl delete namespace agentid --timeout=120s"
        kubectl delete namespace agentid --timeout=120s 2>$null | Out-Null
        Write-Host "  Namespace deleted."
    } else {
        Write-Host "  (namespace 'agentid' not found or cluster not reachable — skipping)"
    }
} else {
    Write-Host "DRY-RUN: kubectl delete namespace agentid --timeout=120s"
}

# ----------------------------------------------------------------------
# Step 5: Delete resource group (AKS + ACR + LB + PVCs).
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "Step 5 — Delete resource group $env:RG (in sub $env:SUBSCRIPTION_ID)"
if (-not $DryRun) {
    & az account set --subscription $env:SUBSCRIPTION_ID
    $rgExists = (& az group exists --name $env:RG) -eq "true"
    if ($rgExists) {
        Write-Host "+ az group delete --name $env:RG --yes --no-wait"
        & az group delete --name $env:RG --yes --no-wait
        Write-Host "  Deletion initiated (--no-wait). Check status: az group show -n $env:RG"
    } else {
        Write-Host "  (RG does not exist — skipping)"
    }
} else {
    Write-Host "DRY-RUN: az account set --subscription $env:SUBSCRIPTION_ID"
    Write-Host "DRY-RUN: az group delete --name $env:RG --yes --no-wait"
}

# ----------------------------------------------------------------------
# Step 6: Entra cleanup (opt-in).
# ----------------------------------------------------------------------
if ($DeleteEntra) {
    Write-Host ""
    Write-Host "Step 6 — Delete Entra objects (in tenant $env:TENANT_ID)"
    if ($env:CLIENT_SPA_APP_ID -and (Confirm-Step "Delete Client SPA ($env:CLIENT_SPA_APP_ID)?")) {
        Invoke-Step "az ad app delete --id $env:CLIENT_SPA_APP_ID" {
            & az ad app delete --id $env:CLIENT_SPA_APP_ID 2>$null
        }
    }
    if ($env:AGENT_CLIENT_ID -and (Confirm-Step "Delete Agent Identity ($env:AGENT_CLIENT_ID)?")) {
        Invoke-Step "DELETE /beta/agentIdentities/$env:AGENT_CLIENT_ID" {
            Invoke-MgGraphRequest -Method DELETE `
                -Uri "https://graph.microsoft.com/beta/agentIdentities/$env:AGENT_CLIENT_ID" `
                -ErrorAction SilentlyContinue
        }
    }
    Write-Host ""
    Write-Host "  *** Blueprint ($env:BLUEPRINT_APP_ID) is often SHARED across agents. ***"
    if (Confirm-Step "Are you SURE you want to delete the Blueprint?") {
        Invoke-Step "az ad app delete --id $env:BLUEPRINT_APP_ID" {
            & az ad app delete --id $env:BLUEPRINT_APP_ID 2>$null
        }
    }
} else {
    Write-Host ""
    Write-Host "Step 6 — Skipping Entra cleanup (-DeleteEntra not specified)"
}

# ----------------------------------------------------------------------
# Step 7: Verify.
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "Step 7 — Verify"
if ($DryRun) {
    Write-Host "DRY-RUN: skipping verification"
} else {
    $rgRemains = (& az group exists --name $env:RG 2>$null)
    Write-Host "  RG exists?       $rgRemains"
    if ($env:BLUEPRINT_APP_ID) {
        $ficRemain = & az ad app federated-credential list --id $env:BLUEPRINT_APP_ID `
            --query "[?name=='$env:FIC_NAME'] | length(@)" -o tsv 2>$null
        Write-Host "  FICs named '$env:FIC_NAME' remaining on Blueprint: $($ficRemain ?? '?')"
    }
    if ($DeleteEntra -and $env:CLIENT_SPA_APP_ID) {
        $spaCheck = & az ad app show --id $env:CLIENT_SPA_APP_ID 2>&1 | Select-Object -First 1
        Write-Host "  Client SPA:      $spaCheck"
    }
}

Write-Host ""
Write-Host "Done. If -DryRun, re-run with -DryRun:`$false to actually delete."
