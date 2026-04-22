# Troubleshooting matrix

| Symptom | Root cause | Fix |
|---|---|---|
| `ollama_available: false` in `/api/status` | Ollama container failed to start or pull model | Check logs with `az containerapp logs show --container ollama`; bump memory; switch to `baked` strategy |
| Ollama container crash-loops with `out of memory` | Model too large for allocated memory | Drop to 1.5B model, or bump ollama memory (see [ollama-on-aca.md](./ollama-on-aca.md)) |
| Ollama logs show `pulling manifest…` then 404 | Model name / tag wrong | Verify exact name with `docker run --rm ollama/ollama:latest ollama pull <name>` locally |
| First request hangs 30+ s | `runtime-pull` strategy cold start | Switch to `baked` strategy (`build-ollama-image.sh`) |
| `AADSTS65001: consent not granted` on OBO sign-in | Agent SP has app perms only, not delegated `User.Read` | Run `scripts/grant-agent-obo-consent.ps1` |
| `AADSTS50011: redirect URI mismatch` in browser | SPA app has only `http://localhost:3003` | Run `scripts/add-spa-redirect-uri.sh` |
| Graph `$filter=appId eq` returns empty for Blueprint | Agent Identity Blueprint types invisible to `$filter` | Use key-lookup form `/beta/applications(appId='<id>')` — scripts already do this |
| `Directory.AccessAsUser.All` scope required (pwsh) | `az account get-access-token --resource graph` includes this scope, which Blueprint PATCH rejects | Use `Connect-MgGraph -Scopes …` with narrow scopes (never `.default`) |
| `403 Authorization_RequestDenied` on Blueprint create | User has `Application Administrator` but not an Agent ID role | Assign `Agent ID Developer` or `Agent ID Administrator` |
| `AADSTS50079` on `az login` | New user hasn't completed MFA enrollment | Sign in once via browser to enroll, then retry |
| Container App fails to pull image (`ImagePullBackOff`) | MI doesn't have `AcrPull` on the registry | `az role assignment create --assignee-object-id "$MI_OBJECT_ID" --assignee-principal-type ServicePrincipal --scope "$ACR_ID" --role AcrPull` |
| Container Apps rejects total CPU/memory | Invalid consumption combo | Totals across all containers must match a valid ACA combo. Demo: 0.5+0.25+0.25+0.75 vCPU = 1.75; 1+0.5+0.5+1.5 = 3.5 Gi |
| Sidecar startup error about `ClientSecret` | Left over docker-compose env var | Ensure manifest uses `AzureAd__ClientCredentials__0__SourceType=SignedAssertionFromManagedIdentity` with empty `ManagedIdentityClientId` for system-assigned |
| ACA ingress returns 504 on first chat | Ollama cold-loading large model; exceeded 4-min ingress timeout | Use smaller model or Dedicated profile |

## Diagnostic one-liners

```bash
# Verify MI object ID
az containerapp show -g "$RG" -n "$APP_NAME" --query identity.principalId -o tsv

# Verify Blueprint federated credential subject
az rest --method GET --url "https://graph.microsoft.com/beta/applications(appId='$BLUEPRINT_APP_ID')/federatedIdentityCredentials"

# Verify Ollama served model list
curl -sS "https://${APP_FQDN}/api/status" | python3 -m json.tool

# Tail Ollama logs
az containerapp logs show -g "$RG" -n "$APP_NAME" --container ollama --tail 50

# Tail sidecar logs (for Entra auth errors)
az containerapp logs show -g "$RG" -n "$APP_NAME" --container sidecar --tail 50
```
