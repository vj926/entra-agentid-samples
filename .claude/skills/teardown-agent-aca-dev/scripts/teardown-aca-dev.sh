#!/usr/bin/env bash
# Teardown orchestrator for deploy-agent-aca-dev.
# Safe by default: DRY_RUN=1, DELETE_ENTRA=0.
#
# Usage:
#   bash teardown-aca-dev.sh                              # dry-run, Azure only
#   DRY_RUN=0 bash teardown-aca-dev.sh                    # real, Azure only
#   DRY_RUN=0 DELETE_ENTRA=1 bash teardown-aca-dev.sh     # full

set -u
set -o pipefail

: "${VARS_FILE:=/tmp/deploy-vars.sh}"
: "${DRY_RUN:=1}"
: "${DELETE_ENTRA:=0}"

if [[ -f "$VARS_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$VARS_FILE"
else
  echo "ERROR: $VARS_FILE not found. Re-export SUBSCRIPTION_ID, TENANT_ID, RG (and CLIENT_SPA_APP_ID / AGENT_CLIENT_ID / BLUEPRINT_APP_ID if deleting those)." >&2
  exit 1
fi

: "${SUBSCRIPTION_ID:?SUBSCRIPTION_ID required in $VARS_FILE}"
: "${RG:?RG required in $VARS_FILE}"

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN: $*"
  else
    echo "+ $*"
    eval "$@"
  fi
}

confirm() {
  local prompt="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY-RUN: would prompt '$prompt' — assuming yes"
    return 0
  fi
  read -r -p "$prompt [y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]]
}

echo "=============================================="
echo "Teardown plan (dev / Ollama ACA deployment)"
echo "  Tenant:          ${TENANT_ID:-<unset>}"
echo "  Subscription:    $SUBSCRIPTION_ID"
echo "  Resource group:  $RG   (WILL be deleted)"
echo "  Delete Entra:    $DELETE_ENTRA (Client SPA, Agent, Blueprint)"
echo "  Dry run:         $DRY_RUN"
echo "=============================================="
confirm "Proceed?" || { echo "Aborted."; exit 0; }

run "az account set --subscription '$SUBSCRIPTION_ID'"

# -- Step 1: revoke OAuth grants on Agent SP --
if [[ -n "${AGENT_CLIENT_ID:-}" ]]; then
  echo ""
  echo "Step 1 — Revoke OAuth consent grants on Agent SP ($AGENT_CLIENT_ID)"
  AGENT_SP_OID=$(az ad sp show --id "$AGENT_CLIENT_ID" --query id -o tsv 2>/dev/null || true)
  if [[ -n "$AGENT_SP_OID" ]]; then
    GRANTS=$(az rest --method GET \
      --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?\$filter=clientId eq '$AGENT_SP_OID'" \
      --query 'value[].id' -o tsv 2>/dev/null || true)
    if [[ -n "$GRANTS" ]]; then
      while IFS= read -r g; do
        [[ -n "$g" ]] && run "az rest --method DELETE --uri 'https://graph.microsoft.com/v1.0/oauth2PermissionGrants/$g'"
      done <<< "$GRANTS"
    else
      echo "  (no grants found)"
    fi
  else
    echo "  (Agent SP not found — skipping)"
  fi
fi

# -- Step 2: delete the RG --
echo ""
echo "Step 2 — Delete resource group $RG"
if az group show --name "$RG" >/dev/null 2>&1; then
  run "az group delete --name '$RG' --yes --no-wait"
else
  echo "  (RG does not exist — skipping)"
fi

# -- Step 3: Entra cleanup (opt-in) --
if [[ "$DELETE_ENTRA" == "1" ]]; then
  echo ""
  echo "Step 3 — Delete Entra objects"
  if [[ -n "${CLIENT_SPA_APP_ID:-}" ]] && confirm "Delete Client SPA (CLIENT_SPA_APP_ID=$CLIENT_SPA_APP_ID)?"; then
    run "az ad app delete --id '$CLIENT_SPA_APP_ID' 2>/dev/null || true"
  fi
  if [[ -n "${AGENT_CLIENT_ID:-}" ]] && confirm "Delete Agent Identity (AGENT_CLIENT_ID=$AGENT_CLIENT_ID)?"; then
    echo "  NOTE: delete the Agent Identity via the Agent ID portal or Graph:"
    echo "    az rest --method DELETE --uri 'https://graph.microsoft.com/beta/agentIdentities/$AGENT_CLIENT_ID'"
  fi
  if [[ -n "${BLUEPRINT_APP_ID:-}" ]]; then
    echo ""
    echo "  *** Blueprint ($BLUEPRINT_APP_ID) is often SHARED across agents. ***"
    if confirm "Are you SURE you want to delete the Blueprint?"; then
      run "az ad app delete --id '$BLUEPRINT_APP_ID' 2>/dev/null || true"
    fi
  fi
else
  echo ""
  echo "Step 3 — Skipping Entra cleanup (DELETE_ENTRA=0)"
fi

# -- Step 4: verify --
echo ""
echo "Step 4 — Verify"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "DRY-RUN: skipping verification"
else
  echo "  RG exists?       $(az group exists --name "$RG")"
  [[ "$DELETE_ENTRA" == "1" && -n "${CLIENT_SPA_APP_ID:-}" ]] && \
    echo "  Client SPA:      $(az ad app show --id "$CLIENT_SPA_APP_ID" 2>&1 | head -1)"
fi

echo ""
echo "Done. If DRY_RUN=1, re-run with DRY_RUN=0 to actually delete."
