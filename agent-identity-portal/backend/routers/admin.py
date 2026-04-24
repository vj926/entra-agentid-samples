"""Admin endpoints — audit log, stats."""

from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, AuditLogRow, BlueprintRow, IdentityRequestRow, PermissionRequestRow
from models import AuditLogOut
from auth import require_approver, get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/audit-log", response_model=list[AuditLogOut])
def get_audit_log(
    limit: int = 50,
    entity_type: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_approver),
):
    limit = min(limit, 500)  # Cap at 500
    q = db.query(AuditLogRow)
    if entity_type:
        q = q.filter(AuditLogRow.entity_type == entity_type)
    return q.order_by(AuditLogRow.performed_at.desc()).limit(limit).all()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    blueprint_counts = {
        "pending": db.query(BlueprintRow).filter(BlueprintRow.status == "pending").count(),
        "active": db.query(BlueprintRow).filter(BlueprintRow.status == "active").count(),
        "deprecated": db.query(BlueprintRow).filter(BlueprintRow.status == "deprecated").count(),
    }
    identity_counts = {
        "pending": db.query(IdentityRequestRow).filter(IdentityRequestRow.status == "pending").count(),
        "provisioned": db.query(IdentityRequestRow).filter(IdentityRequestRow.status == "provisioned").count(),
        "rejected": db.query(IdentityRequestRow).filter(IdentityRequestRow.status == "rejected").count(),
        "failed": db.query(IdentityRequestRow).filter(IdentityRequestRow.status == "failed").count(),
    }
    perm_counts = {
        "pending": db.query(PermissionRequestRow).filter(PermissionRequestRow.status == "pending").count(),
        "granted": db.query(PermissionRequestRow).filter(PermissionRequestRow.status == "granted").count(),
        "rejected": db.query(PermissionRequestRow).filter(PermissionRequestRow.status == "rejected").count(),
        "failed": db.query(PermissionRequestRow).filter(PermissionRequestRow.status == "failed").count(),
    }
    return {
        "blueprints": blueprint_counts,
        "identity_requests": identity_counts,
        "permission_requests": perm_counts,
        "active_blueprints": blueprint_counts["active"],
        "provisioned_identities": identity_counts["provisioned"],
        "granted_permissions": perm_counts["granted"],
        "pending_approvals": blueprint_counts["pending"] + identity_counts["pending"] + perm_counts["pending"],
    }
