"""Approval workflow — handles blueprint, identity, and permission requests."""

from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import (
    get_db,
    BlueprintRow,
    IdentityRequestRow,
    PermissionRequestRow,
    AuditLogRow,
    new_id,
    utcnow,
)
from models import ApprovalAction
from auth import require_approver
from config import settings

logger = logging.getLogger("approvals")

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])


# ── List all pending requests ────────────────────────────────────
@router.get("/pending")
def list_pending(
    db: Session = Depends(get_db),
    user: dict = Depends(require_approver),
):
    blueprint_reqs = (
        db.query(BlueprintRow)
        .filter(BlueprintRow.status == "pending")
        .order_by(BlueprintRow.created_at.asc())
        .all()
    )
    identity_reqs = (
        db.query(IdentityRequestRow)
        .filter(IdentityRequestRow.status == "pending")
        .order_by(IdentityRequestRow.requested_at.asc())
        .all()
    )
    perm_reqs = (
        db.query(PermissionRequestRow)
        .filter(PermissionRequestRow.status == "pending")
        .order_by(PermissionRequestRow.requested_at.asc())
        .all()
    )
    return {
        "blueprint_requests": blueprint_reqs,
        "identity_requests": identity_reqs,
        "permission_requests": perm_reqs,
    }


# ── Approve / reject a blueprint ────────────────────────────────
@router.post("/blueprint/{blueprint_id}")
def decide_blueprint(
    blueprint_id: str,
    action: ApprovalAction,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(require_approver),
):
    row = db.query(BlueprintRow).filter(BlueprintRow.id == blueprint_id).first()
    if not row:
        raise HTTPException(404, "Blueprint not found")
    if row.status != "pending":
        raise HTTPException(400, f"Blueprint is already {row.status}")

    approver = user.get("preferred_username", "admin")
    now = utcnow()

    if action.decision == "approve":
        row.status = "active"
        # Provision the blueprint in Entra ID in the background
        background.add_task(_provision_blueprint, row.id)
    else:
        row.status = "deprecated"

    db.add(
        AuditLogRow(
            id=new_id(),
            entity_type="blueprint",
            entity_id=row.id,
            action=f"blueprint_{action.decision}d",
            performed_by=approver,
            performed_at=now,
            details={"name": row.name, "reason": action.reason} if action.reason else {"name": row.name},
        )
    )
    db.commit()
    db.refresh(row)
    return row


# ── Approve / reject an identity request ────────────────────────
@router.post("/identity/{request_id}")
def decide_identity_request(
    request_id: str,
    action: ApprovalAction,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(require_approver),
):
    row = (
        db.query(IdentityRequestRow)
        .filter(IdentityRequestRow.id == request_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Request not found")
    if row.status != "pending":
        raise HTTPException(400, f"Request is already {row.status}")

    approver = user.get("preferred_username", "admin")
    now = utcnow()

    if action.decision == "approve":
        row.status = "approved"
        row.approved_by = approver
        row.approved_at = now

        # Trigger provisioning in background
        background.add_task(_provision_identity, row.id)
    else:
        row.status = "rejected"
        row.approved_by = approver
        row.approved_at = now
        row.rejection_reason = action.reason

    db.add(
        AuditLogRow(
            id=new_id(),
            entity_type="identity_request",
            entity_id=row.id,
            action=action.decision,
            performed_by=approver,
            performed_at=now,
            details={"reason": action.reason} if action.reason else {},
        )
    )
    db.commit()
    db.refresh(row)
    return row


# ── Approve / reject a permission request ───────────────────────
@router.post("/permission/{request_id}")
def decide_permission_request(
    request_id: str,
    action: ApprovalAction,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(require_approver),
):
    row = (
        db.query(PermissionRequestRow)
        .filter(PermissionRequestRow.id == request_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Request not found")
    if row.status != "pending":
        raise HTTPException(400, f"Request is already {row.status}")

    approver = user.get("preferred_username", "admin")
    now = utcnow()

    if action.decision == "approve":
        row.status = "approved"
        row.approved_by = approver
        row.approved_at = now

        background.add_task(_grant_permissions, row.id)
    else:
        row.status = "rejected"
        row.approved_by = approver
        row.approved_at = now
        row.rejection_reason = action.reason

    db.add(
        AuditLogRow(
            id=new_id(),
            entity_type="permission_request",
            entity_id=row.id,
            action=action.decision,
            performed_by=approver,
            performed_at=now,
            details={"reason": action.reason} if action.reason else {},
        )
    )
    db.commit()
    db.refresh(row)
    return row


# ── Background provisioning tasks ───────────────────────────────
def _provision_blueprint(blueprint_id: str):
    """Create the agentIdentityBlueprint in Entra ID (mock or live)."""
    from services.provisioning import provision_blueprint
    import traceback

    db = next(get_db())
    try:
        row = db.query(BlueprintRow).filter(BlueprintRow.id == blueprint_id).first()
        if not row:
            return
        try:
            result = provision_blueprint(
                display_name=row.name,
                description=row.description,
                agent_type=row.agent_type,
                permission_mode=row.permission_mode,
                permissions=row.default_permissions or [],
            )
            row.provisioned_app_id = result["app_id"]
            row.provisioned_object_id = result["object_id"]
            logger.info("Blueprint %s provisioned: appId=%s", row.name, result["app_id"])
        except Exception as exc:
            logger.error("Blueprint provisioning failed for %s: %s\n%s", blueprint_id, exc, traceback.format_exc())

        db.add(
            AuditLogRow(
                id=new_id(),
                entity_type="blueprint",
                entity_id=row.id,
                action="blueprint_provisioned" if row.provisioned_app_id else "blueprint_provision_failed",
                performed_by="system",
                performed_at=utcnow(),
                details={"app_id": row.provisioned_app_id} if row.provisioned_app_id else {},
            )
        )
        db.commit()
    finally:
        db.close()


def _provision_identity(request_id: str):
    """Create the app registration (mock or live)."""
    from services.provisioning import provision_agent_identity
    import traceback

    db = next(get_db())
    try:
        row = db.query(IdentityRequestRow).filter(IdentityRequestRow.id == request_id).first()
        if not row:
            return
        try:
            # Look up the blueprint's Entra appId (not the local DB id)
            blueprint_app_id = None
            if row.blueprint_id:
                bp = db.query(BlueprintRow).filter(BlueprintRow.id == row.blueprint_id).first()
                if bp and bp.provisioned_app_id:
                    blueprint_app_id = bp.provisioned_app_id

            result = provision_agent_identity(
                display_name=row.display_name,
                description=row.description,
                agent_type=row.agent_type,
                blueprint_app_id=blueprint_app_id,
            )
            row.provisioned_app_id = result["app_id"]
            row.provisioned_object_id = result["object_id"]
            row.status = "provisioned"
        except Exception as exc:
            row.status = "failed"
            error_detail = str(exc)
            # Log full error server-side but sanitize for client
            if hasattr(exc, 'response') and exc.response is not None:
                try:
                    error_detail = f"{exc} | Response: {exc.response.text}"
                except Exception:
                    pass
            logger.error("Provisioning failed for %s: %s", request_id, error_detail)
            # Store only a safe message for the end user
            row.rejection_reason = "Provisioning failed. Contact your administrator for details."

        db.add(
            AuditLogRow(
                id=new_id(),
                entity_type="identity_request",
                entity_id=row.id,
                action="provisioned" if row.status == "provisioned" else "provision_failed",
                performed_by="system",
                performed_at=utcnow(),
                details={"app_id": row.provisioned_app_id} if row.provisioned_app_id else {},
            )
        )
        db.commit()
    finally:
        db.close()


def _grant_permissions(request_id: str):
    """Grant permissions on the app registration (mock or live)."""
    from services.provisioning import grant_agent_permissions

    db = next(get_db())
    try:
        row = db.query(PermissionRequestRow).filter(PermissionRequestRow.id == request_id).first()
        if not row:
            return
        try:
            grant_agent_permissions(
                app_id=row.identity_app_id,
                permissions=row.requested_permissions,
            )
            row.status = "granted"
        except Exception as exc:
            row.status = "failed"
            row.rejection_reason = f"Permission grant error: {exc}"

        db.add(
            AuditLogRow(
                id=new_id(),
                entity_type="permission_request",
                entity_id=row.id,
                action="granted" if row.status == "granted" else "grant_failed",
                performed_by="system",
                performed_at=utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()
