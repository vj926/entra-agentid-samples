# Create resource group, ACR, and an AKS cluster with OIDC issuer +
# Azure Workload Identity enabled, then attach ACR.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

foreach ($v in @('TENANT_ID','SUBSCRIPTION_ID','RG','LOCATION','AKS_NAME','ACR_NAME','NODE_COUNT','NODE_VM_SIZE')) {
    if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($v))) {
        throw "$v is required. Source your deploy-vars.ps1 first."
    }
}
if (-not $env:SUBSCRIPTION_TENANT_ID) { $env:SUBSCRIPTION_TENANT_ID = $env:TENANT_ID }

# Verify az CLI is authenticated to the tenant that owns the subscription.
$currentTenant = (& az account show --query tenantId -o tsv 2>$null).Trim()
if ($currentTenant -ne $env:SUBSCRIPTION_TENANT_ID) {
    Write-Error "az CLI is signed into tenant '$currentTenant' but the target subscription lives in tenant '$env:SUBSCRIPTION_TENANT_ID'."
    Write-Error "Run:  az login --tenant $env:SUBSCRIPTION_TENANT_ID"
    exit 1
}

& az account set --subscription $env:SUBSCRIPTION_ID

Write-Host "[1/4] Resource group"
& az group create -n $env:RG -l $env:LOCATION -o none

Write-Host "[2/4] ACR ($env:ACR_NAME)"
try {
    & az acr create -g $env:RG -n $env:ACR_NAME --sku Basic --admin-enabled false -o none 2>$null
} catch { <# already exists — continue #> }

Write-Host "[3/4] AKS cluster ($env:AKS_NAME) — OIDC + Workload Identity"
& az aks create `
    -g $env:RG -n $env:AKS_NAME `
    --location $env:LOCATION `
    --node-count $env:NODE_COUNT `
    --node-vm-size $env:NODE_VM_SIZE `
    --enable-oidc-issuer `
    --enable-workload-identity `
    --enable-managed-identity `
    --generate-ssh-keys `
    -o none

Write-Host "[4/4] Attach ACR to AKS (grants kubelet AcrPull)"
& az aks update -g $env:RG -n $env:AKS_NAME --attach-acr $env:ACR_NAME -o none

$oidcIssuer = (& az aks show -g $env:RG -n $env:AKS_NAME --query "oidcIssuerProfile.issuerUrl" -o tsv).Trim()
$env:OIDC_ISSUER = $oidcIssuer

# Write OIDC_ISSUER back to the vars file (replace existing line or append).
$varsFile = if ($env:VARS_FILE) { $env:VARS_FILE } else {
    Join-Path ([System.IO.Path]::GetTempPath()) "deploy-vars.ps1"
}
$newLine = "`$env:OIDC_ISSUER = `"$oidcIssuer`""
if (Test-Path $varsFile) {
    $text = Get-Content $varsFile -Raw
    if ($text -match '(?m)^\$env:OIDC_ISSUER\s*=') {
        $text = [regex]::Replace($text, '(?m)^\$env:OIDC_ISSUER\s*=.*', $newLine)
        Set-Content -Path $varsFile -Value $text -NoNewline
    } else {
        Add-Content -Path $varsFile -Value $newLine
    }
} else {
    Set-Content -Path $varsFile -Value $newLine
}
Write-Host "OIDC issuer: $oidcIssuer"
Write-Host "appended: OIDC_ISSUER to $varsFile"

& az aks get-credentials -g $env:RG -n $env:AKS_NAME --overwrite-existing
kubectl get nodes
