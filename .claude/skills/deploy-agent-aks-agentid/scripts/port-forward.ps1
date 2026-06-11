# port-forward.ps1 — open a loopback tunnel to the llm-agent Service so the
# browser-based OBO sign-in flow works.
#
# Why this exists (AKS-specific):
#   The LoadBalancer Service in 50-ingress.yaml exposes the agent over plain
#   HTTP on a public IP. Browsers do NOT treat http://<raw-IP> as a "secure
#   context", so MSAL.js's PKCE flow (which needs Web Crypto's `crypto.subtle`)
#   is blocked and the sign-in popup never opens. Loopback addresses
#   (localhost, 127.0.0.1) ARE secure-context exempt, so port-forwarding the
#   same Service to localhost makes OBO work without TLS / cert-manager / DNS.
#
# Direct (autonomous) mode does NOT require OBO and works fine on the raw
# LB IP. This script is only needed to exercise the "Sign In" button.
#
# Companion: add-spa-redirect-uri.ps1 registers `http://localhost:8080/` as a
# SPA redirect URI by default for exactly this flow.
#
# Usage:
#   pwsh -NoProfile -File port-forward.ps1                   # foreground, Ctrl-C to stop
#   $env:LOCAL_PORT = "9090"; pwsh -NoProfile -File port-forward.ps1
#
# Env (optional):
#   NAMESPACE    default: agentid
#   SERVICE      default: llm-agent
#   LOCAL_PORT   default: 8080
#   REMOTE_PORT  default: 80

$ErrorActionPreference = 'Stop'

$namespace   = $env:NAMESPACE    ? $env:NAMESPACE    : "agentid"
$service     = $env:SERVICE      ? $env:SERVICE      : "llm-agent"
$localPort   = $env:LOCAL_PORT   ? $env:LOCAL_PORT   : "8080"
$remotePort  = $env:REMOTE_PORT  ? $env:REMOTE_PORT  : "80"

Write-Host "Port-forward: http://localhost:${localPort}  ->  svc/${service}:${remotePort} (ns ${namespace})"
Write-Host "Open this URL in a browser to use OBO sign-in. Ctrl-C to stop."
Write-Host ""

kubectl -n $namespace port-forward "svc/$service" "${localPort}:${remotePort}"
