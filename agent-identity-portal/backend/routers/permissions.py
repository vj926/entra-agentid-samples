"""Permission-request endpoints."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db, PermissionRequestRow, AuditLogRow, new_id, utcnow
from models import PermissionRequestCreate, PermissionRequestOut
from auth import get_current_user
from services.provisioning import validate_permissions_for_agent, BLOCKED_AGENT_PERMISSIONS

router = APIRouter(prefix="/api/permission-requests", tags=["Permission Requests"])


@router.get("/blocked-permissions")
def get_blocked_permissions(user: dict = Depends(get_current_user)):
    """Return the list of Graph permissions blocked for agent identities."""
    return {"blocked": sorted(BLOCKED_AGENT_PERMISSIONS)}


@router.get("", response_model=list[PermissionRequestOut])
def list_requests(
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(PermissionRequestRow)
    # Non-approvers can only see their own requests
    if not user.get("is_approver", False) or mine:
        q = q.filter(
            PermissionRequestRow.requested_by == user.get("preferred_username")
        )
    if status:
        q = q.filter(PermissionRequestRow.status == status)
    return q.order_by(PermissionRequestRow.requested_at.desc()).all()


@router.get("/{request_id}", response_model=PermissionRequestOut)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = (
        db.query(PermissionRequestRow)
        .filter(PermissionRequestRow.id == request_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Request not found")
    # Non-approvers can only see their own requests
    if not user.get("is_approver", False) and row.requested_by != user.get("preferred_username"):
        raise HTTPException(403, "Access denied")
    return row


@router.post("", response_model=PermissionRequestOut, status_code=201)
def create_request(
    body: PermissionRequestCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = PermissionRequestRow(
        id=new_id(),
        identity_app_id=body.identity_app_id,
        identity_display_name=body.identity_display_name,
        requested_permissions=[p.model_dump() for p in body.requested_permissions],
        justification=body.justification,
        requested_by=user.get("preferred_username", "unknown"),
        requested_at=utcnow(),
        status="pending",
    )

    # Validate against blocked permissions
    blocked = validate_permissions_for_agent(
        [p.model_dump() for p in body.requested_permissions]
    )
    if blocked:
        raise HTTPException(
            400,
            f"The following permissions are blocked for agent identities: {', '.join(blocked)}. "
            "See https://learn.microsoft.com/en-us/graph/api/resources/agentid-platform-overview",
        )

    db.add(row)
    db.add(
        AuditLogRow(
            id=new_id(),
            entity_type="permission_request",
            entity_id=row.id,
            action="submitted",
            performed_by=user.get("preferred_username", "unknown"),
            performed_at=utcnow(),
            details={
                "identity": body.identity_display_name,
                "permissions_count": len(body.requested_permissions),
            },
        )
    )
    db.commit()
    db.refresh(row)

    from services.notifications import notify_new_request
    background.add_task(
        notify_new_request, row.id, "permission_request", body.identity_display_name
    )

    return row
