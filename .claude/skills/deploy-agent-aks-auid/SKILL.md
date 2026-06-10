---
name: deploy-agent-aks-auid
description: Provision and deploy the Agent ID User (AUID) demo on AKS using the Microsoft Entra SDK auth-sidecar. Use when the user mentions "AUID", "Agent ID User", "microsoft.graph.agentUser", "digital colleague identity", "AUID on AKS", or wants to demo "an agent acting as its own user" (the non-OBO complement to deploy-agent-aks-dev). The skill is fully self-contained: tenant-setup PowerShell scripts, AKS orchestrator + manifests, and the FastAPI broker / Weather Agent / UI source all live under this skill folder. The auth-sidecar (`mcr.microsoft.com/entra-sdk/auth-sidecar`) performs the full Blueprint → Agent ID → user_fic chain INSIDE the pod; the app code never calls login.microsoftonline.com.
---

# Deploy AUID demo (Agent ID User on AKS)

## When to use this skill
Trigger when the user wants to demonstrate Agent ID User (AUID) — the mode where an Entra Agent Identity has its **own first-class user object** (`microsoft.graph.agentUser`) and the agent calls downstream services **as itself** (no human in the loop).

This is the AUID analog of [`deploy-agent-aks-dev`](../deploy-agent-aks-dev/SKILL.md) (autonomous) and [`deploy-agent-aca-dev`](../deploy-agent-aca-dev/SKILL.md) (OBO). Same Workload Identity + auth-sidecar pattern, specialized for `grant_type=user_fic`.

Do NOT use this skill for:
- **Autonomous Agent flows** (no user dimension) → use [`deploy-agent-aks-dev`](../deploy-agent-aks-dev/SKILL.md).
- **On-Behalf-Of flows** (real human signs in, agent acts on their behalf) → use [`deploy-agent-aks-dev`](../deploy-agent-aks-dev/SKILL.md) with the OBO scripts.
- **"Local dev only" demos.** The auth-sidecar requires Workload Identity (`SignedAssertionFilePath` from a projected SA token); running it locally would require shipping a `BLUEPRINT_CLIENT_SECRET` into the container, which is exactly what this architecture eliminates. AKS (or kind with WI add-ons) only.

## Outcome
After completing this skill the customer will have:
- A `microsoft.graph.agentUser` provisioned in their tenant, parented to their existing Agent Identity app.
- A dedicated **Weather Agent** Entra app registration with an exposed scope, admin-consented for the Agent Identity → Weather Agent grant. Required so the AUID JWT can be **signature-verified** by the downstream service.
- An AKS cluster with OIDC issuer + Workload Identity enabled, an attached ACR with the three demo images, and a Federated Identity Credential on the Blueprint trusting `system:serviceaccount:auid:backend-sa`.
- The demo running at `http://<lb-ip>/` with the four-step UI rendering the live AUID acquisition trace served by the `mcr.microsoft.com/entra-sdk/auth-sidecar` container co-located with the FastAPI broker pod.

**Canonical assets:** [`scripts/`](./scripts/) (Phase 1 — Entra setup), [`deploy/aks/scripts/`](./deploy/aks/scripts/) and [`deploy/aks/manifests/`](./deploy/aks/manifests/) (Phase 2 — AKS deploy), [`backend/`](./backend/), [`weather-agent/`](./weather-agent/), [`ui/`](./ui/) (app code built into the three container images). Permissions/scopes reference: [`PERMISSIONS.md`](./PERMISSIONS.md).

## Prerequisites
1. **Entra role** on the signing-in operator: `Global Administrator`, `Cloud Application Administrator`, or `Agent ID Administrator`. The preflight script verifies the operator's delegated Graph scopes; missing scopes are reported FAIL.
2. **Existing Blueprint + Agent Identity apps.** If the customer doesn't have these yet, run [`entra-agent-id-setup`](../entra-agent-id-setup/SKILL.md) first to mint them.
3. **Blueprint must hold the Graph application role** `AgentIdUser.ReadWrite.IdentityParentedBy` (roleId `4aa6e624-eee0-40ab-bdd8-f9639038a614`). Required so the Blueprint can create the `microsoft.graph.agentUser` parented to the Agent Identity. Preflight verifies this.
4. **Azure subscription** with permission to create a resource group, ACR, and AKS cluster. Quota for ~2 `Standard_D2s_v5` nodes.
5. `pwsh` 7.x, `az` CLI, `kubectl`, `bash`, and either WSL or Linux/macOS for the bash scripts.

> **Cross-tenant deployment** (Azure subscription in tenant A, Entra Agent ID objects in tenant B) is supported. Set `SUBSCRIPTION_TENANT_ID` in `/tmp/deploy-vars.sh`. Default behavior is single-tenant.

## Architecture (what the SDK actually does for you)
```
ServiceAccount  auid/backend-sa
        │  Workload Identity webhook projects an SA token at
        │   /var/run/secrets/azure/tokens/azure-identity-token
        ▼
FIC on Blueprint app   (subject  = system:serviceaccount:auid:backend-sa,
                        audience = api://AzureADTokenExchange)
        │
        ▼
Auth sidecar (localhost:5000)
   reads the SA token via SignedAssertionFilePath, runs the full
   Blueprint FIC → Agent ID FIC → user_fic chain INTERNALLY
        │
        ▼
Backend container gets a fully-formed `Authorization: Bearer <AUID>` header
        │
        ▼
Weather Agent (separate Entra app) verifies signature against tenant JWKS,
checks aud / appid / idtyp=user / upn, then serves the request.
```

The backend code ([`backend/sidecar_client.py`](./backend/sidecar_client.py)) **never touches `login.microsoftonline.com`** — it only does a single GET to `http://localhost:5000/AuthorizationHeaderUnauthenticated/weather?AgentIdentity=...&AgentUsername=...`.

## Pre-flight checklist (DO NOT SKIP)

```powershell
pwsh -NoProfile -File .claude/skills/deploy-agent-aks-auid/scripts/00-preflight-check.ps1
```

The script signs the operator in (device code) and produces a colored PASS / FAIL / WARN report for every permission, scope, app role, service principal, and federated identity credential required by the AUID flow. It exits non-zero if anything is FAIL, so you can wire it into CI.

See [`PERMISSIONS.md`](./PERMISSIONS.md) for the complete list of what's checked and how to remediate each FAIL — broken down by:
- **Admin operator** (delegated Graph scopes needed to run the scripts)
- **Blueprint app** (Graph **app role** `AgentIdUser.ReadWrite.IdentityParentedBy` + SP)
- **Agent Identity app** (SP + Federated Identity Credential trusting the Blueprint)
- **Agentic User** (delegated `oauth2PermissionGrant` for `User.Read` AllPrincipals on Agent Identity SP → Graph SP)
- **Weather Agent app** (separate registration with exposed scope + admin-consent grant — **required**, no longer optional)

If preflight fails, **do not run any later script** — talk through the FAIL rows first. Common blockers:
1. Blueprint SP missing app role `AgentIdUser.ReadWrite.IdentityParentedBy` → step 1.1 returns `403 Authorization_RequestDenied`.
2. Agent Identity app has no Federated Identity Credential trusting the Blueprint → sidecar token chain fails with `AADSTS700016` / `invalid_client`.
3. Admin's delegated token missing `AppRoleAssignment.ReadWrite.All` → can't grant the Blueprint app role programmatically.
4. Multi-scope browser admin-consent URL splitting `GroupMember.Read.All` → `AADSTS650053` — use step 1.2 script which posts to `oauth2PermissionGrants` directly.
5. Weather Agent app not registered or admin consent missing → sidecar logs `AADSTS65001` / `consent_required` when fetching the AUID token.

---

## Phase 1 — One-time Entra setup (PowerShell, from your laptop)

### Step 1.1 — Provision the Agentic User
```powershell
pwsh -NoProfile -File .claude/skills/deploy-agent-aks-auid/scripts/01-provision-agentic-user.ps1 `
    -TenantId            <TENANT_ID> `
    -BlueprintAppId      <BLUEPRINT_APP_ID> `
    -AgentIdentityAppId  <AGENT_IDENTITY_APP_ID>
```
Uses an app-only token from the Blueprint (with the `AgentIdUser.ReadWrite.IdentityParentedBy` app role) to POST `/v1.0/users` with `@odata.type=#microsoft.graph.agentUser` and `identityParentId=<AgentIdentityAppId>`. Prints `AGENT_USER_UPN` and `AGENT_USER_OBJECT_ID` — copy these for Phase 2.

> Running this with a delegated admin token (even Global Admin) returns `403 Authorization_RequestDenied`. The Blueprint **must** hold the application role.

### Step 1.2 — Grant the Agentic User delegated Graph access
```powershell
pwsh -NoProfile -File .claude/skills/deploy-agent-aks-auid/scripts/02-grant-agentic-user-consent.ps1 `
    -TenantId           <TENANT_ID> `
    -AgentIdentityAppId <AGENT_IDENTITY_APP_ID>
```
Grants `User.Read` for `AllPrincipals` on the Agent Identity service principal via `oauth2PermissionGrants`. We do this programmatically — **not** via the browser admin-consent URL, because the consent prompt page incorrectly splits `GroupMember.Read.All` into `GroupMember.Read` and fails with `AADSTS650053`.

### Step 1.3 — Register the Weather Agent app (REQUIRED)
```powershell
pwsh -NoProfile -File .claude/skills/deploy-agent-aks-auid/scripts/04-register-weather-app.ps1 `
    -TenantId           <TENANT_ID> `
    -AgentIdentityAppId <AGENT_IDENTITY_APP_ID>
```
- Creates a separate Entra app registration for the Weather Agent.
- Sets `identifierUris = [api://<weatherAppId>]` and exposes a `Weather.Read` scope.
- Creates the SP and grants the Agent Identity SP an admin-consented `oauth2PermissionGrant` (AllPrincipals) for `Weather.Read` on the Weather SP.
- Prints `WEATHER_AGENT_APP_ID` and `WEATHER_AGENT_APP_ID_URI` — copy these for Phase 2.

> **Why this is required** (it used to be optional): the previous revision asked the AUID token for `https://graph.microsoft.com/.default`. Graph tokens carry a `nonce` claim in the JWT header that prevents third parties from cryptographically verifying the signature. The Weather Agent now performs **full RS256 verification against the tenant JWKS**, so the AUID token must be issued for the Weather Agent's own audience.

---

## Phase 2 — Deploy to AKS

### Step 2.1 — Fill in deploy-vars
```bash
cp .claude/skills/deploy-agent-aks-auid/deploy/aks/scripts/deploy-vars.sh.template /tmp/deploy-vars.sh
# Edit /tmp/deploy-vars.sh — set:
#   TENANT_ID, SUBSCRIPTION_ID, RG, LOCATION, AKS_NAME, ACR_NAME (globally unique),
#   BLUEPRINT_APP_ID, AGENT_IDENTITY_APP_ID,
#   AGENT_USER_UPN, AGENT_USER_OBJECT_ID  (from Step 1.1),
#   WEATHER_AGENT_APP_ID, WEATHER_AGENT_APP_ID_URI  (from Step 1.3)
```

### Step 2.2 — Run the orchestrator
```bash
source /tmp/deploy-vars.sh
az login --tenant "${SUBSCRIPTION_TENANT_ID:-$TENANT_ID}"
az account set --subscription "$SUBSCRIPTION_ID"

bash .claude/skills/deploy-agent-aks-auid/deploy/aks/scripts/deploy-aks-dev.sh
```

The orchestrator does:
1. [`01-create-aks.sh`](./deploy/aks/scripts/01-create-aks.sh) — RG + ACR + AKS (OIDC issuer + Workload Identity on, attach-acr). Appends `OIDC_ISSUER` to deploy-vars.
2. [`02-build-and-push.sh`](./deploy/aks/scripts/02-build-and-push.sh) — `az acr build` for `backend`, `weather-agent`, `ui`.
3. [`03-federate-blueprint.ps1`](./deploy/aks/scripts/03-federate-blueprint.ps1) — adds the FIC `system:serviceaccount:auid:backend-sa` to the Blueprint app (audience `api://AzureADTokenExchange`).
4. [`04-apply-manifests.sh`](./deploy/aks/scripts/04-apply-manifests.sh) — `envsubst` + `kubectl apply` for [`00-namespace`](./deploy/aks/manifests/00-namespace.yaml), [`10-serviceaccount`](./deploy/aks/manifests/10-serviceaccount.yaml), [`20-weather-agent`](./deploy/aks/manifests/20-weather-agent.yaml), [`30-ui`](./deploy/aks/manifests/30-ui.yaml) (LoadBalancer), [`40-backend`](./deploy/aks/manifests/40-backend.yaml) (broker + `mcr.microsoft.com/entra-sdk/auth-sidecar` co-located in the same pod).

When the LB IP is assigned, open `http://<lb-ip>/` and click through the 4-step demo. Step 3 calls the sidecar (which performs the full Blueprint→AgentID→user_fic chain internally and returns the AUID Authorization header); step 4 hits the Weather Agent and shows the validated AUID claims.

---

## Phase 3 — Smoke-test the AUID acquisition

```bash
kubectl get pods -n auid

# Sidecar logs — look for "Acquired token for downstream API 'weather'"
kubectl logs -n auid -l app=backend -c sidecar --tail=80

# Backend logs
kubectl logs -n auid -l app=backend -c backend --tail=80

# Hit the broker's step-03 endpoint from inside the pod:
kubectl exec -n auid deploy/backend -c backend -- \
  curl -s -X POST http://localhost:8080/api/step/03-auid-token | head -c 800
```

Expected: `"ok": true`, an `authorization_header_preview` like `Bearer eyJ...`, and the request showing `AgentIdentity=<AGENT_IDENTITY_APP_ID>` + `AgentUsername=<AGENT_USER_UPN>`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|--|--|--|
| Step 1.1 returns `403 Authorization_RequestDenied` | Trying to create `agentUser` with a delegated admin token | Blueprint SP must hold the **application** role `AgentIdUser.ReadWrite.IdentityParentedBy`. Grant via `POST /servicePrincipals/{bpSpId}/appRoleAssignments`. |
| Step 1.2 fails `AADSTS650053` (`GroupMember.Read doesn't exist`) | Multi-scope browser admin-consent URL splits scopes wrong | Use [`scripts/02-grant-agentic-user-consent.ps1`](./scripts/02-grant-agentic-user-consent.ps1) instead of the browser. |
| `deploy-aks-dev.sh` exits at start with `ERROR: $WEATHER_AGENT_APP_ID unset` | Skipped Step 1.3 | Run [`scripts/04-register-weather-app.ps1`](./scripts/04-register-weather-app.ps1), copy the printed values into `/tmp/deploy-vars.sh`, re-source. |
| Sidecar logs `AADSTS700016` / `invalid_client` | Blueprint FIC for `system:serviceaccount:auid:backend-sa` not present | Re-run [`deploy/aks/scripts/03-federate-blueprint.ps1`](./deploy/aks/scripts/03-federate-blueprint.ps1). Confirm `OIDC_ISSUER` was appended to deploy-vars and re-sourced. |
| Sidecar logs `AADSTS65001` / `consent_required` | Agent Identity → Weather Agent admin consent missing | Re-run [`scripts/04-register-weather-app.ps1`](./scripts/04-register-weather-app.ps1), or grant via `POST /v1.0/oauth2PermissionGrants` (`clientId=<aiSpId>`, `resourceId=<weatherSpId>`, `consentType=AllPrincipals`, `scope="Weather.Read"`). |
| `/api/step/03-auid-token` returns connection-refused | Sidecar container not running, or `SIDECAR_URL` env wrong | `kubectl describe pod` and check the `sidecar` container is Ready. Manifest expects `SIDECAR_URL=http://localhost:5000`. |
| Weather Agent returns `Signature verification failed` | AUID token was issued for Graph audience instead of Weather Agent | Verify `WEATHER_AGENT_APP_ID_URI` is set in the manifest env and that `DownstreamApis__weather__Scopes__0` resolves to `api://<weather>/.default` in the sidecar config. |
| `Connect-MgGraph -UseDeviceCode` device code never prints | PowerShell async pipe doesn't flush the prompt | Hit `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode` directly with `Invoke-RestMethod` to surface the code. |
| PS 5.1 fails to load Microsoft.Graph 2.x | Module needs PS7 | Use `pwsh`. |

---

## Files in this skill

### Phase 1 — Entra setup ([`scripts/`](./scripts/))
- [`scripts/00-preflight-check.ps1`](./scripts/00-preflight-check.ps1) — verifies every Entra prerequisite, PASS/FAIL/WARN report.
- [`scripts/01-provision-agentic-user.ps1`](./scripts/01-provision-agentic-user.ps1) — creates the `microsoft.graph.agentUser` parented to the Agent Identity.
- [`scripts/02-grant-agentic-user-consent.ps1`](./scripts/02-grant-agentic-user-consent.ps1) — grants delegated `User.Read` for AllPrincipals (Agent Identity → Graph).
- [`scripts/04-register-weather-app.ps1`](./scripts/04-register-weather-app.ps1) — registers the Weather Agent app, exposes `Weather.Read`, grants admin consent (Agent Identity → Weather Agent).

### Phase 2 — AKS deploy ([`deploy/aks/`](./deploy/aks/))
- [`deploy/aks/scripts/deploy-vars.sh.template`](./deploy/aks/scripts/deploy-vars.sh.template) — variables file you copy to `/tmp/deploy-vars.sh`.
- [`deploy/aks/scripts/01-create-aks.sh`](./deploy/aks/scripts/01-create-aks.sh) — RG + ACR + AKS (OIDC + WI on, attach-acr).
- [`deploy/aks/scripts/02-build-and-push.sh`](./deploy/aks/scripts/02-build-and-push.sh) — `az acr build` for the three images.
- [`deploy/aks/scripts/03-federate-blueprint.ps1`](./deploy/aks/scripts/03-federate-blueprint.ps1) — adds the FIC on the Blueprint app.
- [`deploy/aks/scripts/04-apply-manifests.sh`](./deploy/aks/scripts/04-apply-manifests.sh) — `envsubst` + `kubectl apply` for everything in `manifests/`.
- [`deploy/aks/scripts/deploy-aks-dev.sh`](./deploy/aks/scripts/deploy-aks-dev.sh) — one-shot orchestrator.
- [`deploy/aks/manifests/`](./deploy/aks/manifests/) — `00-namespace`, `10-serviceaccount`, `20-weather-agent`, `30-ui` (LB), `40-backend` (broker + auth-sidecar containers).

### Application code (built into the three container images)
- [`backend/app.py`](./backend/app.py) — FastAPI broker exposing each step + a one-shot `/api/call-weather` endpoint. Calls only the sidecar — never `login.microsoftonline.com`.
- [`backend/sidecar_client.py`](./backend/sidecar_client.py) — thin async wrapper around `GET /AuthorizationHeaderUnauthenticated/<svc>?AgentIdentity=...&AgentUsername=...`.
- [`weather-agent/app.py`](./weather-agent/app.py) — downstream service; performs full RS256 signature + claim validation against the tenant JWKS.
- [`ui/index.html`](./ui/index.html), [`ui/nginx.conf`](./ui/nginx.conf) — single-page UI; nginx proxies `/api/*` to the backend Service.
- [`.env.example`](./.env.example) — local sample of the env vars; the AKS manifests source the real values from `/tmp/deploy-vars.sh` via `envsubst`.

---

## Customer hand-off checklist

- [ ] Customer ran [`scripts/00-preflight-check.ps1`](./scripts/00-preflight-check.ps1) and **all rows are PASS** (warnings may be acceptable — review with them).
- [ ] Tenant ID, Blueprint App ID, Agent Identity App ID confirmed with customer.
- [ ] Blueprint SP holds `AgentIdUser.ReadWrite.IdentityParentedBy` (app role).
- [ ] Agent Identity has a FIC trusting the Blueprint app.
- [ ] Agentic User provisioned and Agent Identity → Graph `User.Read` AllPrincipals grant exists.
- [ ] Weather Agent app registered, scope exposed, Agent Identity → Weather Agent admin-consent grant exists.
- [ ] `deploy-aks-dev.sh` completed without error and `kubectl get pods -n auid` shows `backend` (2/2 — backend + sidecar), `weather-agent`, `ui` all `Running`.
- [ ] `kubectl logs -n auid -l app=backend -c sidecar` shows `Acquired token for downstream API 'weather'`.
- [ ] LB UI at `http://<lb-ip>/` shows green PASS rows for steps 1–4 and a real weather response with the validated AUID claims.
- [ ] Customer understands the **OBO vs AUID** distinction.
- [ ] Customer understands that **local-only execution is not supported** and why (Workload Identity prerequisite).
- [ ] Customer has a copy of [`PERMISSIONS.md`](./PERMISSIONS.md) for ongoing reference.
