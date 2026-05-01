---
name: teardown-agent-aca-dev
description: 'AI-led teardown of the local-LLM (Ollama) sample agent deployment on Azure Container Apps created by deploy-agent-aca-dev. Use when the user wants to delete the dev sample ACA deployment, clean up the resource group, or optionally delete the Blueprint / Agent Identity / Client SPA. Defaults to DRY-RUN and keeps Entra objects unless the user explicitly opts in. NOT for local docker-compose (use `docker compose down -v`) and NOT for the AWS Bedrock variant (use teardown-agent-aca-aws).'
---

# Teardown — Dev (Ollama) Agent on Azure Container Apps (AI-Led)

Reverses the `deploy-agent-aca-dev` skill. Deletes the Azure resource group and (opt-in) the Entra objects.

**Paired with:** [deploy-agent-aca-dev](../deploy-agent-aca-dev/SKILL.md). Uses the same `/tmp/deploy-vars.sh`.

## When to Use

- User says: "tear down the dev ACA deployment", "delete the Ollama agent on Azure", "clean up the demo RG"
- User wants to re-run the deploy skill from a clean state
- User is ending a demo and needs to remove billable resources (ACA, ACR with Ollama images, Log Analytics)

## Do NOT Use When

- **Local docker-compose** — `cd sidecar/dev && docker compose down -v` is enough
- **AWS variant** — use [teardown-agent-aca-aws](../teardown-agent-aca-aws/SKILL.md) (handles IAM role, OIDC provider, intermediary app)
- **Shared / long-lived tenants** — confirm the Blueprint and Client SPA are not shared with other agents first

## Safety posture

1. **Dry-run by default** (`DRY_RUN=1`). User must set `DRY_RUN=0` to actually delete.
2. **Entra objects are opt-in** (`DELETE_ENTRA=1`). Default keeps them.
3. **Confirm tenant + subscription + RG** with the user first — the user has multiple Azure accounts.
4. **Re-confirm before deleting the Blueprint.** Blueprints are often shared.

## Prerequisites

- `/tmp/deploy-vars.sh` from the original deployment (at minimum `SUBSCRIPTION_ID`, `RG`).
- `az` logged in to the correct tenant + subscription.
- Graph role sufficient to delete Entra apps (only if `DELETE_ENTRA=1`): `Application Administrator` or higher.

## Procedure

### Step 0 — Confirm scope

```
Teardown plan (dev / Ollama):
  Subscription:  $SUBSCRIPTION_ID
  Resource group: $RG            (WILL be deleted)
  Delete Entra objects: $DELETE_ENTRA
  Dry run:              $DRY_RUN
Proceed? [y/N]
```

### Step 1 — Revoke OAuth consent grants on the Agent SP

If keeping the Agent Identity, revoke existing consent so a redeploy starts clean:

```bash
AGENT_SP_OID=$(az ad sp show --id "$AGENT_CLIENT_ID" --query id -o tsv 2>/dev/null)
if [[ -n "$AGENT_SP_OID" ]]; then
  az rest --method GET \
    --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?\$filter=clientId eq '$AGENT_SP_OID'" \
    --query 'value[].id' -o tsv | while read -r g; do
      az rest --method DELETE --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants/$g"
  done
fi
```

### Step 2 — Delete the resource group

```bash
az group delete --name "$RG" --yes --no-wait
```

This removes the Container App, ACA environment, ACR (with the ~1–4 GB baked Ollama image), Log Analytics workspace, and user-assigned managed identity in one shot.

### Step 3 — Delete Entra objects (opt-in: `DELETE_ENTRA=1`)

Ask per object. Order:

1. **Client SPA** (`CLIENT_SPA_APP_ID`) — safe if no other agent reuses it.
2. **Agent Identity** — delete via Agent ID portal or Graph (`DELETE /agentIdentities/{id}`).
3. **Blueprint** (`BLUEPRINT_APP_ID`) — **ASK AGAIN**. Blueprints are often shared.

```bash
az ad app delete --id "$CLIENT_SPA_APP_ID" 2>/dev/null || true
# Agent + Blueprint: prompt explicitly, then call Graph
```

### Step 4 — Verify

```bash
az group exists --name "$RG"                          # expect: false
az ad app show --id "$CLIENT_SPA_APP_ID" 2>&1 | head -1   # expect: not found (if DELETE_ENTRA=1)
```

## Orchestrator

Single-entry-point script: [`scripts/teardown-aca-dev.sh`](./scripts/teardown-aca-dev.sh).

```bash
# Dry run (default)
bash .claude/skills/teardown-agent-aca-dev/scripts/teardown-aca-dev.sh

# Real teardown, Azure only
DRY_RUN=0 bash .claude/skills/teardown-agent-aca-dev/scripts/teardown-aca-dev.sh

# Full teardown (incl. Entra apps)
DRY_RUN=0 DELETE_ENTRA=1 \
  bash .claude/skills/teardown-agent-aca-dev/scripts/teardown-aca-dev.sh
```

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `az group delete` hangs | ACR still has replications or a KV with purge protection is in the RG | Check RG contents with `az resource list -g "$RG"`; delete the stuck resource manually |
| `Authorization_RequestDenied` on `az ad app delete` | Signing-in user lacks `Application Administrator` on the app | Elevate via PIM or have the app owner run it |
| FIC cleanup leaves orphaned entries on Blueprint | MI deleted by `az group delete` | Inert; clean with `az ad app federated-credential list/delete` if cosmetic |
| Baked Ollama image still billing after `az group delete` completes | ACR has a soft-delete retention window | Check: `az acr list --query "[].{n:name,p:properties.policies.softDeletePolicy.status}"`; purge if present |

## References

- [Azure — delete resource group](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/delete-resource-group)
- [Microsoft Graph — oauth2PermissionGrants](https://learn.microsoft.com/en-us/graph/api/oauth2permissiongrant-delete)
