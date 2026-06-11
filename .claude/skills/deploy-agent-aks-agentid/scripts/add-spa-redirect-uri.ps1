# add-spa-redirect-uri.ps1 — register browser sign-in URIs on the Client SPA app.
#
# AKS-specific behavior:
#   1. ALWAYS registers `http://localhost:8080/`. The LoadBalancer exposes the
#      agent over plain HTTP, and raw-IP HTTP is NOT a browser "secure context"
#      — so MSAL.js (which relies on Web Crypto / PKCE) refuses to open the
#      sign-in popup. Loopback IS a secure context, so OBO works via
#      `kubectl port-forward svc/llm-agent 8080:80` (see port-forward.ps1).
#   2. If APP_FQDN is set, ALSO registers `${REDIRECT_SCHEME}://$APP_FQDN/`
#      so the LoadBalancer IP works for autonomous-mode browsing.
#   3. If REDIRECT_URI is set, registers that string verbatim instead.
#
# Cross-tenant aware: TENANT_ID is the Entra tenant where the SPA lives.
# Idempotent — fetches existing spa.redirectUris first, only PATCHes the diff.
#
# Required env vars: CLIENT_SPA_APP_ID, TENANT_ID
# Optional env vars: APP_FQDN, REDIRECT_SCHEME (default http), REDIRECT_URI,
#                    PORT_FORWARD_URI (default http://localhost:8080/)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $env:CLIENT_SPA_APP_ID) { throw "CLIENT_SPA_APP_ID required (from deploy-vars.ps1)." }
if (-not $env:TENANT_ID)         { throw "TENANT_ID required (Entra tenant where the SPA lives)." }

$portForwardUri = if ($null -ne $env:PORT_FORWARD_URI) { $env:PORT_FORWARD_URI } else { "http://localhost:8080/" }
$appFqdn        = $env:APP_FQDN ?? ""
$redirectScheme = $env:REDIRECT_SCHEME ? $env:REDIRECT_SCHEME : "http"
$redirectUri    = $env:REDIRECT_URI ?? ""

if (-not $redirectUri -and $appFqdn) {
    $redirectUri = "${redirectScheme}://${appFqdn}/"
}

Import-Module Microsoft.Graph.Authentication -ErrorAction Stop
Connect-MgGraph -TenantId $env:TENANT_ID -Scopes "Application.ReadWrite.OwnedBy" -NoWelcome | Out-Null

$app = Invoke-MgGraphRequest -Method GET `
    -Uri "https://graph.microsoft.com/v1.0/applications(appId='$($env:CLIENT_SPA_APP_ID)')?`$select=id,spa"

$existingUris = if ($app.spa -and $app.spa.redirectUris) { @($app.spa.redirectUris) } else { @() }

$want = @()
if ($portForwardUri) { $want += $portForwardUri }
if ($redirectUri)    { $want += $redirectUri }

$toAdd = $want | Where-Object { $_ -and ($_ -notin $existingUris) }

if (-not $toAdd) {
    Write-Host "All requested redirect URIs already registered. Nothing to do."
    exit 0
}

$newUris = @($existingUris) + @($toAdd)
$body = @{ spa = @{ redirectUris = $newUris } } | ConvertTo-Json -Depth 5
Invoke-MgGraphRequest -Method PATCH `
    -Uri "https://graph.microsoft.com/v1.0/applications/$($app.id)" `
    -Body $body -ContentType "application/json"

Write-Host "Added SPA redirect URIs: $($toAdd -join ', ')"
