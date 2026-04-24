"""Agent identity provisioning — mock and live (Graph beta Agent ID APIs).

Uses the Microsoft Entra Agent ID building blocks:
  - agentIdentityBlueprint  → POST /beta/applications  (@odata.type)
  - agentIdentity           → created from a blueprint
  - agentIdentityBlueprintPrincipal → tenant registration

See: https://learn.microsoft.com/en-us/graph/api/resources/agentid-platform-overview
"""

from __future__ import annotations
import logging
import uuid
import httpx
import msal
from config import settings

logger = logging.getLogger("provisioning")

GRAPH_BETA = "https://graph.microsoft.com/beta"


# ── Public API ──────────────────────────────────────────────────

def provision_blueprint(
    display_name: str,
    description: str,
    agent_type: str,
    permission_mode: str,
    permissions: list[dict],
) -> dict:
    """Create an agentIdentityBlueprint in Entra ID.

    Returns {"app_id": ..., "object_id": ...}.
    """
    if settings.provisioning_mode == "mock":
        return _mock_provision_blueprint(display_name, description, agent_type, permission_mode, permissions)
    return _live_provision_blueprint(display_name, description, agent_type, permission_mode, permissions)


def provision_agent_identity(
    display_name: str,
    description: str,
    agent_type: str,
    blueprint_app_id: str | None = None,
) -> dict:
    """Create an agentIdentity from a blueprint.

    Returns {"app_id": ..., "object_id": ...}.
    """
    if settings.provisioning_mode == "mock":
        return _mock_provision_identity(display_name, description, agent_type, blueprint_app_id)
    return _live_provision_identity(display_name, description, agent_type, blueprint_app_id)


def grant_agent_permissions(
    app_id: str,
    permissions: list[dict],
) -> None:
    """Add required resource access to an agent identity."""
    if settings.provisioning_mode == "mock":
        _mock_grant(app_id, permissions)
    else:
        _live_grant(app_id, permissions)


# ── Mock implementations ────────────────────────────────────────

def _mock_provision_blueprint(
    display_name: str, description: str, agent_type: str,
    permission_mode: str, permissions: list[dict],
) -> dict:
    app_id = str(uuid.uuid4())
    object_id = str(uuid.uuid4())
    perm_count = len(permissions) if permission_mode == "inheritable" else 0
    logger.info("[MOCK] Created agentIdentityBlueprint %s appId=%s objectId=%s type=%s mode=%s perms=%d",
                display_name, app_id, object_id, agent_type, permission_mode, perm_count)
    return {"app_id": app_id, "object_id": object_id}


def _mock_provision_identity(
    display_name: str, description: str, agent_type: str,
    blueprint_app_id: str | None,
) -> dict:
    app_id = str(uuid.uuid4())
    object_id = str(uuid.uuid4())
    logger.info("[MOCK] Created agentIdentity %s appId=%s objectId=%s blueprintAppId=%s",
                display_name, app_id, object_id, blueprint_app_id)
    return {"app_id": app_id, "object_id": object_id}


def _mock_grant(app_id: str, permissions: list[dict]) -> None:
    for p in permissions:
        logger.info("[MOCK] Granted %s (%s) on %s -> %s",
                    p.get("scope"), p.get("type"), p.get("resource"), app_id)


# ── Graph token acquisition ────────────────────────────────────

def _get_graph_token() -> str:
    """Acquire an app-only Graph token via the shared credentials helper."""
    from services.credentials import get_graph_token
    token = get_graph_token()
    if not token:
        raise RuntimeError(
            "Failed to acquire Graph token. Configure one of: "
            "USE_MANAGED_IDENTITY, AZURE_CLIENT_CERTIFICATE_PATH, "
            "AZURE_CLIENT_SECRET_KEYVAULT_URI, or AZURE_CLIENT_SECRET."
        )
    return token


def _graph_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _graph_call(client, method, url, **kwargs):
    """Make a Graph API call with proper error handling."""
    resp = getattr(client, method)(url, **kwargs)
    if resp.status_code >= 400:
        error_body = ""
        try:
            error_body = resp.json().get("error", {}).get("message", resp.text[:500])
        except Exception:
            error_body = resp.text[:500]
        raise RuntimeError(
            f"Graph API {method.upper()} {url} returned {resp.status_code}: {error_body}"
        )
    return resp


# ── Well-known resource IDs and permission GUIDs ────────────────

_RESOURCE_IDS = {
    "Microsoft Graph": "00000003-0000-0000-c000-000000000000",
}

_GRAPH_APP_PERMISSIONS = {
    "User.Read.All": "df021288-bdef-4463-88db-98f22de89214",
    "Application.Read.All": "9a5d68dd-52b0-4cc2-bd40-abcf44ac3a30",
    "Directory.Read.All": "7ab1d382-f21e-4acd-a863-ba3e13f7da61",
    "Mail.Send": "b633e1c5-b582-4048-a93e-9f11b44c7e96",
    "Mail.Read": "810c84a8-4a9e-49e6-bf7d-12d183f40d01",
    "Group.Read.All": "5b567255-7703-4780-807c-7be8301ae99b",
    "Sites.Read.All": "332a536c-c7ef-4017-ab91-336970924f0d",
    "Chat.Read": "6b7d71aa-70aa-4810-a8d9-5d9fb2830017",
    "Calendars.Read": "798ee544-9d2d-430c-a058-570e29e34338",
    "Files.Read.All": "01d4f6ba-18a1-4129-aa68-3a6e24f2822c",
}

# Permissions blocked for agent identities (from Graph docs)
BLOCKED_AGENT_PERMISSIONS = {
    "Application.ReadWrite.All", "Application.ReadWrite.OwnedBy",
    "AppRoleAssignment.ReadWrite.All", "Directory.ReadWrite.All",
    "Directory.Write.Restricted", "Directory.AccessAsUser.All",
    "Domain.ReadWrite.All", "Group.Create", "Group.ReadWrite.All",
    "GroupMember.ReadWrite.All", "RoleManagement.ReadWrite.Directory",
    "RoleManagement.ReadWrite.All", "User.ReadWrite.All",
    "User.DeleteRestore.All", "User.EnableDisableAccount.All",
    "UserAuthenticationMethod.ReadWrite.All", "UserAuthenticationMethod.Read.All",
    "User-PasswordProfile.ReadWrite.All", "DelegatedPermissionGrant.ReadWrite.All",
    "ConsentRequest.ReadWrite.All", "CustomSecAttributeAssignment.ReadWrite.All",
    "CustomSecAttributeDefinition.ReadWrite.All", "Organization.ReadWrite.All",
    "Policy.ReadWrite.AuthenticationMethod", "Policy.ReadWrite.CrossTenantAccess",
    "Policy.ReadWrite.PermissionGrant", "Policy.ReadWrite.SecurityDefaults",
    "IdentityProvider.ReadWrite.All", "LifecycleManagement.ReadWrite.All",
    "EntitlementManagement.ReadWrite.All", "EduRoster.ReadWrite.All",
    "Device.ReadWrite.All", "Device.Write.Restricted",
    "DeviceManagementConfiguration.Read.All",
    "Files.Read.All", "Files.ReadWrite.All",
    "Sites.Read.All", "Sites.ReadWrite.All", "Sites.Manage.All",
    "Sites.FullControl.All", "Chat.Read.All", "Chat.ReadWrite.All",
    "ChannelMessage.Read.All", "ChannelMessage.Read.Group",
    "PrintJob.ReadWrite.All", "Tasks.ReadWrite.All",
    "BitlockerKey.Read.All", "Calendars.Read",
    "PrivilegedAccess.ReadWrite.AzureAD", "PrivilegedAccess.ReadWrite.AzureResources",
    "User.Invite.All",
    # Agent ID creation permissions (agents can't self-create)
    "AgentIdentity.Create", "AgentIdentity.Create.All",
    "AgentIdentity.CreateAsManager", "AgentIdentityBlueprint.Create",
    "AgentIdentityBlueprint.CreateAsManager", "AgentIdentityBlueprint.ReadWrite.All",
    "AgentIdentityBlueprintPrincipal.Create",
}


def validate_permissions_for_agent(permissions: list[dict]) -> list[str]:
    """Check permissions against the blocked list. Returns list of blocked ones."""
    blocked = []
    for p in permissions:
        if p.get("scope") in BLOCKED_AGENT_PERMISSIONS:
            blocked.append(p["scope"])
    return blocked


# ── Live: Blueprint provisioning ────────────────────────────────

def _build_required_resource_access(permissions: list[dict]) -> list[dict]:
    """Convert permission list to Graph requiredResourceAccess format."""
    resource_access: dict[str, list[dict]] = {}
    for perm in permissions:
        resource_name = perm.get("resource", "Microsoft Graph")
        resource_id = _RESOURCE_IDS.get(resource_name, resource_name)
        scope = perm["scope"]
        perm_type = perm.get("type", "Application")

        if resource_id not in resource_access:
            resource_access[resource_id] = []

        perm_guid = _GRAPH_APP_PERMISSIONS.get(scope, scope)
        resource_access[resource_id].append({
            "id": perm_guid,
            "type": "Role" if perm_type == "Application" else "Scope",
        })

    return [
        {"resourceAppId": res_id, "resourceAccess": accesses}
        for res_id, accesses in resource_access.items()
    ]


def _live_provision_blueprint(
    display_name: str, description: str, agent_type: str,
    permission_mode: str, permissions: list[dict],
) -> dict:
    token = _get_graph_token()

    body = {
        "@odata.type": "#microsoft.graph.agentIdentityBlueprint",
        "displayName": display_name,
        "description": description,
        "signInAudience": "AzureADMyOrg",
        "tags": [
            f"agent-type:{agent_type}",
            f"permission-mode:{permission_mode}",
            "managed-by:agent-identity-portal",
        ],
    }

    # For inheritable mode, set requiredResourceAccess on the blueprint
    if permission_mode == "inheritable" and permissions:
        body["requiredResourceAccess"] = _build_required_resource_access(permissions)

    with httpx.Client(timeout=30) as client:
        # Create the agentIdentityBlueprint
        resp = _graph_call(
            client, "post",
            f"{GRAPH_BETA}/applications",
            json=body,
            headers=_graph_headers(token),
        )
        bp_data = resp.json()
        app_id = bp_data["appId"]
        object_id = bp_data["id"]

        # Create the agentIdentityBlueprintPrincipal (tenant registration)
        _graph_call(
            client, "post",
            f"{GRAPH_BETA}/servicePrincipals",
            json={"appId": app_id},
            headers=_graph_headers(token),
        )

    return {"app_id": app_id, "object_id": object_id}


# ── Live: Agent Identity provisioning ───────────────────────────

def _live_provision_identity(
    display_name: str, description: str, agent_type: str,
    blueprint_app_id: str | None,
) -> dict:
    token = _get_graph_token()

    body = {
        "@odata.type": "#microsoft.graph.agentIdentity",
        "displayName": display_name,
        "description": description,
        "signInAudience": "AzureADMyOrg",
        "tags": [
            f"agent-type:{agent_type}",
            f"blueprint:{blueprint_app_id or 'none'}",
            "managed-by:agent-identity-portal",
        ],
    }

    with httpx.Client(timeout=30) as client:
        # Create the agentIdentity
        resp = _graph_call(
            client, "post",
            f"{GRAPH_BETA}/applications",
            json=body,
            headers=_graph_headers(token),
        )
        app_data = resp.json()
        app_id = app_data["appId"]
        object_id = app_data["id"]

        # Create service principal
        _graph_call(
            client, "post",
            f"{GRAPH_BETA}/servicePrincipals",
            json={"appId": app_id},
            headers=_graph_headers(token),
        )

        # If blueprint has inheritable permissions, copy them to the identity
        if blueprint_app_id:
            try:
                _inherit_blueprint_permissions(client, token, blueprint_app_id, object_id)
            except Exception as exc:
                logger.warning("Could not inherit permissions from blueprint %s: %s", blueprint_app_id, exc)

    return {"app_id": app_id, "object_id": object_id}


def _inherit_blueprint_permissions(client, token: str, blueprint_app_id: str, identity_object_id: str):
    """Copy requiredResourceAccess from a blueprint to an identity."""
    # Look up the blueprint to get its permissions
    bp_resp = _graph_call(
        client, "get",
        f"{GRAPH_BETA}/applications",
        params={"$filter": f"appId eq '{blueprint_app_id}'", "$select": "id,requiredResourceAccess"},
        headers=_graph_headers(token),
    )
    bps = bp_resp.json().get("value", [])
    if not bps:
        logger.warning("Blueprint %s not found for permission inheritance", blueprint_app_id)
        return

    required = bps[0].get("requiredResourceAccess", [])
    if not required:
        logger.info("Blueprint %s has no requiredResourceAccess to inherit", blueprint_app_id)
        return

    # Apply the same permissions to the identity
    _graph_call(
        client, "patch",
        f"{GRAPH_BETA}/applications/{identity_object_id}",
        json={"requiredResourceAccess": required},
        headers=_graph_headers(token),
    )
    logger.info("Inherited %d resource access entries from blueprint %s to identity %s",
                len(required), blueprint_app_id, identity_object_id)


# ── Live: Permission grants ────────────────────────────────────

def _live_grant(app_id: str, permissions: list[dict]) -> None:
    """Grant permissions to an agent identity in Entra ID.

    1. Set requiredResourceAccess on the application (declares intent)
    2. Create appRoleAssignments on the service principal (admin consent for Application perms)
    3. Create oauth2PermissionGrants on the service principal (admin consent for Delegated perms)
    """
    token = _get_graph_token()

    with httpx.Client(timeout=30) as client:
        # Look up the app's object ID
        resp = _graph_call(
            client, "get",
            f"{GRAPH_BETA}/applications",
            params={"$filter": f"appId eq '{app_id}'", "$select": "id"},
            headers=_graph_headers(token),
        )
        apps = resp.json().get("value", [])
        if not apps:
            raise RuntimeError(f"App with appId {app_id} not found")
        object_id = apps[0]["id"]

        # Step 1: Set requiredResourceAccess on the application
        required = _build_required_resource_access(permissions)
        _graph_call(
            client, "patch",
            f"{GRAPH_BETA}/applications/{object_id}",
            json={"requiredResourceAccess": required},
            headers=_graph_headers(token),
        )

        # Step 2: Look up the service principal for this app
        sp_resp = _graph_call(
            client, "get",
            f"{GRAPH_BETA}/servicePrincipals",
            params={"$filter": f"appId eq '{app_id}'", "$select": "id"},
            headers=_graph_headers(token),
        )
        sps = sp_resp.json().get("value", [])
        if not sps:
            # Create the service principal if it doesn't exist
            sp_create = _graph_call(
                client, "post",
                f"{GRAPH_BETA}/servicePrincipals",
                json={"appId": app_id},
                headers=_graph_headers(token),
            )
            sp_id = sp_create.json()["id"]
        else:
            sp_id = sps[0]["id"]

        # Step 3: Grant admin consent for each permission
        app_perms = [p for p in permissions if p.get("type", "Application") == "Application"]
        delegated_perms = [p for p in permissions if p.get("type") == "Delegated"]

        # Application permissions → appRoleAssignments
        for perm in app_perms:
            resource_name = perm.get("resource", "Microsoft Graph")
            resource_app_id = _RESOURCE_IDS.get(resource_name, resource_name)
            scope = perm["scope"]
            role_id = _GRAPH_APP_PERMISSIONS.get(scope)
            if not role_id:
                logger.warning("No known role ID for scope %s — skipping admin consent", scope)
                continue

            # Look up the resource service principal
            res_sp_resp = _graph_call(
                client, "get",
                f"{GRAPH_BETA}/servicePrincipals",
                params={"$filter": f"appId eq '{resource_app_id}'", "$select": "id"},
                headers=_graph_headers(token),
            )
            res_sps = res_sp_resp.json().get("value", [])
            if not res_sps:
                logger.warning("Resource SP for %s not found — skipping", resource_name)
                continue
            resource_sp_id = res_sps[0]["id"]

            try:
                _graph_call(
                    client, "post",
                    f"{GRAPH_BETA}/servicePrincipals/{sp_id}/appRoleAssignments",
                    json={
                        "principalId": sp_id,
                        "resourceId": resource_sp_id,
                        "appRoleId": role_id,
                    },
                    headers=_graph_headers(token),
                )
                logger.info("Admin consent granted: %s (%s) on %s", scope, role_id, resource_name)
            except RuntimeError as exc:
                if "Permission being assigned already exists" in str(exc):
                    logger.info("Permission %s already granted — skipping", scope)
                else:
                    raise

        # Delegated permissions → oauth2PermissionGrants
        if delegated_perms:
            # Group by resource
            by_resource: dict[str, list[str]] = {}
            for perm in delegated_perms:
                resource_name = perm.get("resource", "Microsoft Graph")
                resource_app_id = _RESOURCE_IDS.get(resource_name, resource_name)
                by_resource.setdefault(resource_app_id, []).append(perm["scope"])

            for resource_app_id, scopes in by_resource.items():
                res_sp_resp = _graph_call(
                    client, "get",
                    f"{GRAPH_BETA}/servicePrincipals",
                    params={"$filter": f"appId eq '{resource_app_id}'", "$select": "id"},
                    headers=_graph_headers(token),
                )
                res_sps = res_sp_resp.json().get("value", [])
                if not res_sps:
                    continue
                resource_sp_id = res_sps[0]["id"]

                try:
                    _graph_call(
                        client, "post",
                        f"{GRAPH_BETA}/oauth2PermissionGrants",
                        json={
                            "clientId": sp_id,
                            "consentType": "AllPrincipals",
                            "resourceId": resource_sp_id,
                            "scope": " ".join(scopes),
                        },
                        headers=_graph_headers(token),
                    )
                    logger.info("Delegated consent granted: %s on %s", scopes, resource_app_id)
                except RuntimeError as exc:
                    if "already exists" in str(exc).lower():
                        logger.info("Delegated consent already exists — skipping")
                    else:
                        raise
