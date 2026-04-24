"""Blueprint CRUD endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db, BlueprintRow, IdentityRequestRow, AuditLogRow, new_id, utcnow
from models import BlueprintCreate, BlueprintOut
from auth import get_current_user, require_approver

logger = logging.getLogger("blueprints")

router = APIRouter(prefix="/api/blueprints", tags=["Blueprints"])


@router.get("", response_model=list[BlueprintOut])
def list_blueprints(
    status: str = "active",
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(BlueprintRow)
    if status:
        q = q.filter(BlueprintRow.status == status)
    return q.order_by(BlueprintRow.created_at.desc()).all()


@router.get("/tenant", summary="List all agentIdentityBlueprints from Entra ID tenant")
def list_tenant_blueprints(
    search: str = "",
    user: dict = Depends(get_current_user),
):
    """Query Graph beta to list all agentIdentityBlueprint objects in the tenant.
    
    Merges with local portal blueprints for a unified view.
    """
    import httpx
    import re
    from auth import _get_graph_token_for_role_check

    # Sanitize search input - only allow alphanumerics, dashes, underscores, spaces (<=64 chars).
    if search and not re.fullmatch(r"[A-Za-z0-9 _\-]{1,64}", search):
        raise HTTPException(400, "Invalid search term")

    token = _get_graph_token_for_role_check()
    if not token:
        raise HTTPException(502, "Unable to acquire Graph token for tenant query")

    try:
        params = {
            "$select": "id,appId,displayName,description,tags,createdDateTime,requiredResourceAccess,signInAudience",
            "$top": "100",
        }
        # Filter by odata.type for agentIdentityBlueprint
        # Graph beta supports filtering by type
        if search:
            params["$search"] = f'"displayName:{search}"'

        headers = {
            "Authorization": f"Bearer {token}",
            "ConsistencyLevel": "eventual",
        }

        with httpx.Client() as client:
            resp = client.get(
                "https://graph.microsoft.com/beta/applications",
                params={
                    "$filter": "tags/any(t: t eq 'managed-by:agent-identity-portal') or tags/any(t: t eq 'agentIdentityBlueprint')",
                    "$select": "id,appId,displayName,description,tags,createdDateTime,requiredResourceAccess,signInAudience",
                    "$top": "100",
                    "$count": "true",
                },
                headers=headers,
            )

            if resp.status_code != 200:
                logger.warning("Graph tenant blueprint query returned %d: %s", resp.status_code, resp.text[:200])
                # Fall back to just returning empty — the local DB results still show
                return {"tenant_blueprints": [], "error": "Graph query failed"}

            data = resp.json()
            apps = data.get("value", [])

        # Transform Graph results into a consistent shape
        tenant_bps = []
        for app in apps:
            tags = app.get("tags", [])
            # Determine agent type and permission mode from tags
            agent_type = "custom"
            permission_mode = "manual"
            for tag in tags:
                if tag.startswith("agent-type:"):
                    agent_type = tag.split(":", 1)[1]
                if tag.startswith("permission-mode:"):
                    permission_mode = tag.split(":", 1)[1]

            # Extract permissions from requiredResourceAccess
            perms = []
            for ra in app.get("requiredResourceAccess", []):
                resource_id = ra.get("resourceAppId", "")
                resource_name = "Microsoft Graph" if resource_id == "00000003-0000-0000-c000-000000000000" else resource_id
                for access in ra.get("resourceAccess", []):
                    perms.append({
                        "resource": resource_name,
                        "scope": access.get("id", ""),
                        "type": "Application" if access.get("type") == "Role" else "Delegated",
                    })

            source = "portal" if "managed-by:agent-identity-portal" in tags else "entra"

            tenant_bps.append({
                "id": app.get("id"),
                "app_id": app.get("appId"),
                "name": app.get("displayName", ""),
                "description": app.get("description", ""),
                "agent_type": agent_type,
                "permission_mode": permission_mode,
                "default_permissions": perms,
                "created_at": app.get("createdDateTime"),
                "sign_in_audience": app.get("signInAudience"),
                "source": source,
                "tags": tags,
            })

        return {"tenant_blueprints": tenant_bps, "count": len(tenant_bps)}

    except httpx.HTTPError as exc:
        logger.error("Graph HTTP error querying tenant blueprints: %s", exc)
        return {"tenant_blueprints": [], "error": str(exc)}


@router.get("/{blueprint_id}", response_model=BlueprintOut)
def get_blueprint(
    blueprint_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = db.query(BlueprintRow).filter(BlueprintRow.id == blueprint_id).first()
    if not row:
        raise HTTPException(404, "Blueprint not found")
    return row


@router.post("", response_model=BlueprintOut, status_code=201)
def create_blueprint(
    body: BlueprintCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    requester = user.get("preferred_username", "unknown")
    now = utcnow()
    bp_id = new_id()

    # Validate against blocked Graph permissions for agent identities.
    from services.provisioning import validate_permissions_for_agent
    blocked = validate_permissions_for_agent([p.model_dump() for p in body.default_permissions])
    if blocked:
        raise HTTPException(
            400,
            f"The following permissions are blocked for agent identities: {', '.join(blocked)}. "
            "See https://learn.microsoft.com/en-us/graph/api/resources/agentid-platform-overview",
        )

    # Approvers can create active blueprints; others create pending ones
    initial_status = "active" if user.get("is_approver", False) else "pending"

    row = BlueprintRow(
        id=bp_id,
        name=body.name,
        description=body.description,
        agent_type=body.agent_type,
        permission_mode=body.permission_mode,
        default_permissions=[p.model_dump() for p in body.default_permissions],
        required_apis=body.required_apis,
        created_by=requester,
        created_at=now,
        status=initial_status,
    )

    # For custom/3P agents, auto-create a linked identity request
    if body.agent_type == "custom" and body.identity_display_name:
        ir_id = new_id()
        identity_req = IdentityRequestRow(
            id=ir_id,
            blueprint_id=bp_id,
            display_name=body.identity_display_name,
            description=body.description,
            agent_type=body.agent_type,
            environment=body.identity_environment or "dev",
            justification=body.identity_justification or f"Auto-created with blueprint: {body.name}",
            requested_by=requester,
            requested_at=now,
            status="pending",
        )
        row.linked_identity_request_id = ir_id
        db.add(identity_req)
        db.add(
            AuditLogRow(
                id=new_id(),
                entity_type="identity_request",
                entity_id=ir_id,
                action="submitted",
                performed_by=requester,
                performed_at=now,
                details={
                    "display_name": body.identity_display_name,
                    "linked_blueprint": bp_id,
                    "auto_created": True,
                },
            )
        )

        # Notify approvers about the linked identity request
        from services.notifications import notify_new_request
        background.add_task(
            notify_new_request, ir_id, "identity_request", body.identity_display_name
        )

    db.add(row)
    db.add(
        AuditLogRow(
            id=new_id(),
            entity_type="blueprint",
            entity_id=bp_id,
            action="created",
            performed_by=requester,
            performed_at=now,
            details={
                "name": body.name,
                "linked_identity": row.linked_identity_request_id,
            },
        )
    )
    db.commit()
    db.refresh(row)

    # If approver created as active, provision in Entra in the background
    if initial_status == "active":
        from routers.approvals import _provision_blueprint
        background.add_task(_provision_blueprint, row.id)

    return row


@router.patch("/{blueprint_id}/deprecate", response_model=BlueprintOut)
def deprecate_blueprint(
    blueprint_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_approver),
):
    row = db.query(BlueprintRow).filter(BlueprintRow.id == blueprint_id).first()
    if not row:
        raise HTTPException(404, "Blueprint not found")
    row.status = "deprecated"
    db.add(
        AuditLogRow(
            id=new_id(),
            entity_type="blueprint",
            entity_id=row.id,
            action="deprecated",
            performed_by=user.get("preferred_username", "unknown"),
            performed_at=utcnow(),
        )
    )
    db.commit()
    db.refresh(row)
    return row
