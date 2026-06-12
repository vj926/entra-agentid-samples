---
name: teardown-agent-aks-auid
description: 'AI-led teardown of the Entra Agent ID User (AUID) demo deployed to AKS by deploy-agent-aks-auid. Removes the k8s namespace, resource group (AKS + ACR), FIC on the Blueprint, Agentic User object, Weather Agent app registration, OAuth grants, and optionally the Blueprint and Agent Identity. Safe by default: -DryRun is $true, -DeleteEntra is $false. Cross-tenant aware. Pairs with deploy-agent-aks-auid.'
---

# Teardown — Entra Agent ID User (AUID) Demo on AKS (AI-Led)

Reverses the [`deploy-agent-aks-auid`](../deploy-agent-aks-auid/SKILL.md) skill. Removes every object the deploy and Entra setup scripts create.

**Paired with:** [`deploy-agent-aks-auid`](../deploy-agent-aks-auid/SKILL.md).

## What this removes

| Object | Script that created it | Condition |
|---|---|---|
| k8s `auid` namespace (graceful pod termination) | `04-apply-manifests.ps1` | always |
| FIC on Blueprint (`aks-backend-sa`) | `03-federate-blueprint.ps1` | always |
| OAuth consent grants on Agent Identity SP | `02-grant-agentic-user-consent.ps1` | always |
| Weather Agent app registration + SP | `04-register-weather-app.ps1` | always |
| Resource group (AKS + ACR + LB + PVCs) | `01-create-aks.ps1` | always |
| Agentic User (`microsoft.graph.agentUser`) | `01-provision-agentic-user.ps1` | `-DeleteEntra` |
| Agent Identity app | `entra-agent-id-setup` | `-DeleteEntra` |
| Blueprint app | `entra-agent-id-setup` | `-DeleteEntra` (prompted again) |

## Safety posture

1. **Dry-run by default** (`-DryRun` is `$true`). Must pass `-DryRun:$false` to actually delete.
2. **Entra objects are opt-in** (`-DeleteEntra`). Default keeps Blueprint, Agent Identity, Agentic User.
3. **Blueprint re-confirmed** — even with `-DeleteEntra`, the orchestrator prompts again before deleting the Blueprint because Blueprints are frequently shared.
4. **Confirm tenant + subscription** with the user before running. Wrong-tenant teardowns are unrecoverable.

## Prerequisites

1. Your `deploy-vars.ps1` (at minimum: `SUBSCRIPTION_ID`, `RG`, `TENANT_ID`, `BLUEPRINT_APP_ID`; also `AGENT_IDENTITY_APP_ID`, `WEATHER_AGENT_APP_ID`, `AGENT_USER_UPN` if cleaning those).
2. `az` logged into both tenants for cross-tenant deploys.
3. `pwsh` 7.4+ with `Microsoft.Graph.Authentication` (`Install-Module Microsoft.Graph.Authentication -Scope CurrentUser`).
4. **Graph roles**: `Application.ReadWrite.OwnedBy` (FIC + Weather Agent app); `User.ReadWrite.All` (Agentic User delete); `Application.ReadWrite.All` if using `-DeleteEntra`.

## One-Shot Orchestrator

```powershell
$env:VARS_FILE = "$HOME/deploy-vars-auid.ps1"

# Dry run — prints all steps, deletes nothing
pwsh -NoProfile -File .claude/skills/teardown-agent-aks-auid/scripts/teardown-aks-auid.ps1

# Real teardown — k8s namespace + RG + FIC + OAuth grants + Weather Agent app
pwsh -NoProfile -File .claude/skills/teardown-agent-aks-auid/scripts/teardown-aks-auid.ps1 -DryRun:$false

# Full teardown — everything above + Agentic User + Agent Identity + Blueprint (each prompted)
pwsh -NoProfile -File .claude/skills/teardown-agent-aks-auid/scripts/teardown-aks-auid.ps1 -DryRun:$false -DeleteEntra

# Just remove the FIC (no RG touch)
pwsh -NoProfile -File .claude/skills/teardown-agent-aks-auid/scripts/teardown-aks-auid.ps1 -FicOnly
```

## Cross-tenant teardown

| Step | Tenant used |
|---|---|
| Revoke OAuth grants, delete FIC, delete Weather Agent app, delete Agentic User | `$TENANT_ID` (Entra objects) |
| Delete RG | `$SUBSCRIPTION_TENANT_ID` (Azure subscription) |

## References

- [`deploy-agent-aks-auid`](../deploy-agent-aks-auid/SKILL.md) — the deploy skill this reverses
- [`deploy-agent-aks-auid/PERMISSIONS.md`](../deploy-agent-aks-auid/PERMISSIONS.md) — full Graph scope reference
