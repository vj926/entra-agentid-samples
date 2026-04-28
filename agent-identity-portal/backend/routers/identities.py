"""Identity-request endpoints."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db, IdentityRequestRow, AuditLogRow, new_id, utcnow
from models import IdentityRequestCreate, IdentityRequestOut
from auth import get_current_user

router = APIRouter(prefix="/api/identity-requests", tags=["Identity Requests"])


@router.get("", response_model=list[IdentityRequestOut])
def list_requests(
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(IdentityRequestRow)
    # Non-approvers can only see their own requests
    if not user.get("is_approver", False) or mine:
        q = q.filter(
            IdentityRequestRow.requested_by == user.get("preferred_username")
        )
    if status:
        q = q.filter(IdentityRequestRow.status == status)
    return q.order_by(IdentityRequestRow.requested_at.desc()).all()


@router.get("/{request_id}", response_model=IdentityRequestOut)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = db.query(IdentityRequestRow).filter(IdentityRequestRow.id == request_id).first()
    if not row:
        raise HTTPException(404, "Request not found")
    # Non-approvers can only see their own requests
    if not user.get("is_approver", False) and row.requested_by != user.get("preferred_username"):
        raise HTTPException(403, "Access denied")
    return row


@router.post("", response_model=IdentityRequestOut, status_code=201)
def create_request(
    body: IdentityRequestCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = IdentityRequestRow(
        id=new_id(),
        blueprint_id=body.blueprint_id,
        display_name=body.display_name,
        description=body.description,
        agent_type=body.agent_type,
        environment=body.environment,
        justification=body.justification,
        requested_by=user.get("preferred_username", "unknown"),
        requested_at=utcnow(),
        status="pending",
    )
    db.add(row)
    db.add(
        AuditLogRow(
            id=new_id(),
            entity_type="identity_request",
            entity_id=row.id,
            action="submitted",
            performed_by=user.get("preferred_username", "unknown"),
            performed_at=utcnow(),
            details={"display_name": body.display_name, "agent_type": body.agent_type},
        )
    )
    db.commit()
    db.refresh(row)

    # Notify approvers in the background
    from services.notifications import notify_new_request
    background.add_task(notify_new_request, row.id, "identity_request", body.display_name)

    return row
