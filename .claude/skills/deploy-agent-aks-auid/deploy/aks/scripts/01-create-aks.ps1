# Create RG, ACR, and AKS cluster with OIDC issuer + Workload Identity enabled.
# Appends OIDC_ISSUER back to the vars file (idempotent: replaces existing line).
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

foreach ($v in @('SUBSCRIPTION_ID','RG','LOCATION','AKS_NAME','ACR_NAME','NODE_VM_SIZE','NODE_COUNT','ACR_SKU')) {
    if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($v))) {
        throw "$v is required. Source your deploy-vars.ps1 first."
    }
}

$varsFile = if ($env:VARS_FILE) { $env:VARS_FILE } else {
    Join-Path ([System.IO.Path]::GetTempPath()) "deploy-vars.ps1"
}

& az account set --subscription $env:SUBSCRIPTION_ID

# Resource group (idempotent)
$rgExists = (& az group show -n $env:RG 2>$null) -ne $null
if (-not $rgExists) {
    Write-Host "Creating resource group $env:RG..."
    & az group create -n $env:RG -l $env:LOCATION -o none
}

# ACR (idempotent)
$acrExists = (& az acr show -n $env:ACR_NAME -g $env:RG 2>$null) -ne $null
if (-not $acrExists) {
    Write-Host "Creating ACR $env:ACR_NAME..."
    & az acr create -n $env:ACR_NAME -g $env:RG --sku $env:ACR_SKU -o none
}

# AKS cluster (idempotent)
$aksExists = (& az aks show -n $env:AKS_NAME -g $env:RG 2>$null) -ne $null
if (-not $aksExists) {
    Write-Host "Creating AKS cluster $env:AKS_NAME..."
    & az aks create `
        -n $env:AKS_NAME -g $env:RG -l $env:LOCATION `
        --node-count $env:NODE_COUNT --node-vm-size $env:NODE_VM_SIZE `
        --enable-oidc-issuer --enable-workload-identity `
        --attach-acr $env:ACR_NAME `
        --generate-ssh-keys -o none
} else {
    Write-Host "AKS cluster $env:AKS_NAME already exists — ensuring OIDC + Workload Identity are enabled..."
    & az aks update -n $env:AKS_NAME -g $env:RG `
        --enable-oidc-issuer --enable-workload-identity -o none 2>$null
    & az aks update -n $env:AKS_NAME -g $env:RG --attach-acr $env:ACR_NAME -o none 2>$null
}

& az aks get-credentials -n $env:AKS_NAME -g $env:RG --overwrite-existing

$oidcIssuer = (& az aks show -n $env:AKS_NAME -g $env:RG --query oidcIssuerProfile.issuerUrl -o tsv).Trim()
$env:OIDC_ISSUER = $oidcIssuer

# Persist OIDC_ISSUER in the vars file (replace existing line or append).
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
Write-Host "appended: OIDC_ISSUER=$oidcIssuer"
