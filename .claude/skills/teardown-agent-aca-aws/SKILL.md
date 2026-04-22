---
name: teardown-agent-aca-aws
description: 'AI-led teardown of the AWS Bedrock sample agent deployment on Azure Container Apps created by deploy-agent-aca-aws. Use when the user wants to delete the AWS sample ACA deployment, clean up the resource group, remove the AWS IAM role + OIDC provider, delete the intermediary Entra app, or optionally delete the Blueprint / Agent Identity / Client SPA. Defaults to DRY-RUN and keeps Entra/AWS objects unless the user explicitly opts in. NOT for local docker-compose (no cloud resources to delete) and NOT for GCP (pending).'
---

# Teardown — AWS Bedrock Agent on Azure Container Apps (AI-Led)

Reverses the `deploy-agent-aca-aws` skill. Deletes Azure resources, the AWS IAM role and OIDC provider, and (opt-in) the Entra objects created along the way.

**Paired with:** [deploy-agent-aca-aws](../deploy-agent-aca-aws/SKILL.md). Uses the same `/tmp/deploy-vars.sh` produced by that skill.

## When to Use

- User says: "tear down the AWS ACA deployment", "delete the Azure resources for the AWS sample", "clean up after the demo"
- User wants to re-run the deploy skill from a clean state
- User is ending a demo and needs to remove billable resources

## Do NOT Use When

- **Local dev** — `sidecar/dev/` runs in docker-compose; `docker compose down -v` is enough
- **Shared / long-lived tenants** — do not run this against a tenant where other teams may own the Blueprint or Client SPA. Confirm ownership with the user first.
- **Hardened / long-lived deployments** — this skill assumes a throwaway demo deployment.

## Safety posture

This skill is destructive. To prevent accidents:

1. **Dry-run by default.** Every script defaults to `DRY_RUN=1` — it prints the commands it would run and exits. The user must explicitly set `DRY_RUN=0` to actually delete.
2. **Entra and AWS objects are opt-in.** Default behavior deletes only the Azure resource group. Entra apps (Agent Identity, Blueprint, Client SPA, Intermediary) and AWS objects (IAM role, OIDC provider) are preserved unless the user sets `DELETE_ENTRA=1` or `DELETE_AWS=1`.
3. **Confirm the tenant + subscription + resource group** with the user before running anything. The user has multiple Azure accounts (see user memory).
4. **Never auto-delete Blueprints** — Blueprints may be shared across agents. If `DELETE_ENTRA=1`, ask the user one more time: "Delete Blueprint `<id>`? y/N".

## Prerequisites

- `/tmp/deploy-vars.sh` from the original deployment (contains `RG`, `STS_APP_ID`, `AWS_ROLE_NAME`, `AWS_ACCOUNT_ID`, `TENANT_ID`, etc.). If missing, reconstruct the minimum set with the user (at least `SUBSCRIPTION_ID`, `RG`).
- `az` logged in to the same tenant and subscription that owns the RG.
- `aws` configured for the same account that owns the role (only if `DELETE_AWS=1`).
- Graph role sufficient to delete Entra apps (only if `DELETE_ENTRA=1`): `Application Administrator` or higher.

## Procedure

### Step 0 — Confirm scope with the user

Print the current settings and wait for explicit confirmation:

```
Teardown plan (AWS):
  Subscription:  $SUBSCRIPTION_ID
  Resource group: $RG            (WILL be deleted)
  Delete AWS IAM role + OIDC:  $DELETE_AWS
  Delete Entra objects:         $DELETE_ENTRA
  Dry run:                      $DRY_RUN
Proceed? [y/N]
```

Do not proceed without a `y`.

### Step 1 — Revoke OAuth consent grants on the Agent SP (optional but recommended)

If the Agent Identity (`AGENT_CLIENT_ID`) will be kept, revoke the Graph OAuth2 consent so a future redeploy starts from a clean state:

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

This is idempotent — if the SP or the grants are gone already, it no-ops.

### Step 2 — Delete the Azure resource group

This removes the Container App, ACA environment, ACR (with all images), Log Analytics workspace, and the user-assigned managed identity in one shot:

```bash
az group delete --name "$RG" --yes --no-wait
```

**Note:** FICs on the Blueprint and Intermediary Entra apps that point at the deleted MI's object ID become orphaned but inert. They are cleaned up in Step 4 if `DELETE_ENTRA=1`, or can be left in place — they cannot be re-used since the MI they reference no longer exists.

### Step 3 — Delete AWS objects (opt-in: `DELETE_AWS=1`)

```bash
aws iam delete-role-policy --role-name "$AWS_ROLE_NAME" --policy-name BedrockInvokeOnly 2>/dev/null || true
aws iam delete-role --role-name "$AWS_ROLE_NAME" 2>/dev/null || true
aws iam delete-open-id-connect-provider \
  --open-id-connect-provider-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/sts.windows.net/${TENANT_ID}/" 2>/dev/null || true
```

### Step 4 — Delete Entra objects (opt-in: `DELETE_ENTRA=1`)

Ask the user once more per object. Delete in this order to avoid broken references:

1. **Intermediary app** (`STS_APP_ID`) — safe to delete, created purely for AWS federation.
2. **Client SPA** (`CLIENT_SPA_APP_ID`) — safe if no other agent reuses it.
3. **Agent Identity** — delete via Agent ID portal or Graph (`DELETE /agentIdentities/{id}`).
4. **Blueprint** (`BLUEPRINT_APP_ID`) — **ASK AGAIN**. Blueprints are often shared.

```bash
az ad app delete --id "$STS_APP_ID" 2>/dev/null || true
az ad app delete --id "$CLIENT_SPA_APP_ID" 2>/dev/null || true
# Agent + Blueprint: prompt explicitly, then call Graph
```

### Step 5 — Verify

```bash
az group exists --name "$RG"                                          # expect: false
aws iam get-role --role-name "$AWS_ROLE_NAME" 2>&1 | head -1          # expect: NoSuchEntity (if DELETE_AWS=1)
az ad app show --id "$STS_APP_ID" 2>&1 | head -1                      # expect: not found (if DELETE_ENTRA=1)
```

## Orchestrator

The single-entry-point script is [`scripts/teardown-aca-aws.sh`](./scripts/teardown-aca-aws.sh). It reads `/tmp/deploy-vars.sh`, enforces dry-run by default, prompts at every destructive boundary, and executes steps 1–5 in order.

```bash
# Dry run (default)
bash .claude/skills/teardown-agent-aca-aws/scripts/teardown-aca-aws.sh

# Real teardown, Azure only
DRY_RUN=0 bash .claude/skills/teardown-agent-aca-aws/scripts/teardown-aca-aws.sh

# Full teardown
DRY_RUN=0 DELETE_AWS=1 DELETE_ENTRA=1 \
  bash .claude/skills/teardown-agent-aca-aws/scripts/teardown-aca-aws.sh
```

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `az group delete` hangs on soft-deleted Key Vault | RG contained a KV with purge protection | Purge separately: `az keyvault purge --name <kv>` |
| `DeleteConflict` on IAM role | Role still attached to an instance profile or has inline policies | The script deletes `BedrockInvokeOnly` first; if extra policies exist, list + detach them manually |
| `Authorization_RequestDenied` on `az ad app delete` | Signing-in user lacks `Application Administrator` on the app | Have the app owner run it, or elevate via PIM |
| FIC cleanup leaves orphaned entries on Blueprint | MI already deleted by `az group delete` | Inert — delete via `az ad app federated-credential list/delete` if cosmetic cleanup matters |
| OIDC provider already in use by another role | Shared across multiple role bindings in the same account | Do NOT delete the OIDC provider; leave `DELETE_AWS=0` or delete only the role |

## References

- [Azure — delete resource group](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/delete-resource-group)
- [AWS IAM — delete OIDC identity provider](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_manage-oidc.html)
- [Microsoft Graph — oauth2PermissionGrants](https://learn.microsoft.com/en-us/graph/api/oauth2permissiongrant-delete)
