"""Pydantic schemas for API request/response bodies."""

from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
import re

_GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


# ── Enums ────────────────────────────────────────────────────────
AgentType = Literal["copilot_studio", "foundry", "custom"]
Environment = Literal["dev", "staging", "production"]
BlueprintStatus = Literal["pending", "active", "deprecated"]
RequestStatus = Literal["pending", "approved", "rejected", "provisioned", "failed"]
PermissionStatus = Literal["pending", "approved", "rejected", "granted", "failed"]
PermissionType = Literal["Delegated", "Application"]


# ── Permission entry ────────────────────────────────────────────
class PermissionEntry(BaseModel):
    resource: str = Field(..., min_length=1, max_length=128, description="API resource, e.g. Microsoft Graph")
    scope: str = Field(..., min_length=1, max_length=128, description="Permission scope, e.g. User.Read")
    type: PermissionType = "Application"


PermissionMode = Literal["inheritable", "manual"]


# ── Blueprint ────────────────────────────────────────────────────
class BlueprintCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field("", max_length=1024)
    agent_type: AgentType
    permission_mode: PermissionMode = "inheritable"
    default_permissions: list[PermissionEntry] = []
    required_apis: list[str] = []
    # For custom/3P agents — identity created alongside blueprint
    identity_display_name: Optional[str] = Field(None, max_length=256)
    identity_environment: Optional[Environment] = None
    identity_justification: Optional[str] = Field(None, max_length=2000)

    @field_validator("default_permissions")
    @classmethod
    def _cap_perms(cls, v):
        if len(v) > 50:
            raise ValueError("Too many default permissions (max 50)")
        return v

    @field_validator("required_apis")
    @classmethod
    def _cap_apis(cls, v):
        if len(v) > 20:
            raise ValueError("Too many required_apis (max 20)")
        return v


class BlueprintOut(BlueprintCreate):
    id: str
    created_by: str
    created_at: datetime
    status: BlueprintStatus
    linked_identity_request_id: Optional[str] = None
    provisioned_app_id: Optional[str] = None
    provisioned_object_id: Optional[str] = None


# ── Identity Request ────────────────────────────────────────────
class IdentityRequestCreate(BaseModel):
    blueprint_id: Optional[str] = None
    display_name: str = Field(..., max_length=256)
    description: str = Field("", max_length=1024)
    agent_type: AgentType
    environment: Environment = "dev"
    justification: str = Field("", max_length=2000)


class IdentityRequestOut(IdentityRequestCreate):
    id: str
    requested_by: str
    requested_at: datetime
    status: RequestStatus
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    provisioned_app_id: Optional[str] = None
    provisioned_object_id: Optional[str] = None
    rejection_reason: Optional[str] = None


# ── Permission Request ──────────────────────────────────────────
class PermissionRequestCreate(BaseModel):
    identity_app_id: str = Field(..., max_length=100)
    identity_display_name: str = Field(..., max_length=256)
    requested_permissions: list[PermissionEntry]
    justification: str = Field("", max_length=2000)

    @field_validator("identity_app_id")
    @classmethod
    def _validate_appid(cls, v: str) -> str:
        if not _GUID_RE.match(v):
            raise ValueError("identity_app_id must be a GUID")
        return v

    @field_validator("requested_permissions")
    @classmethod
    def _nonempty_perms(cls, v):
        if not v:
            raise ValueError("At least one permission must be requested")
        if len(v) > 50:
            raise ValueError("Too many permissions requested (max 50)")
        return v


class PermissionRequestOut(PermissionRequestCreate):
    id: str
    requested_by: str
    requested_at: datetime
    status: PermissionStatus
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


# ── Approval action ─────────────────────────────────────────────
class ApprovalAction(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = ""


# ── Audit log ───────────────────────────────────────────────────
class AuditLogOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    performed_by: str
    performed_at: datetime
    details: dict = {}
