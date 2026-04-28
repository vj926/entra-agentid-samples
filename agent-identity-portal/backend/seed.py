"""Seed the database with demo data if tables are empty.

Seeding is gated behind ``SEED_DEMO_DATA`` (default ``false``) so real
customer deployments never pick up fake rows. All identifiers use
``example.com`` so the sample can be shared publicly.
"""

import logging
import os
from sqlalchemy.orm import Session
from database import (
    SessionLocal, BlueprintRow, IdentityRequestRow, PermissionRequestRow, AuditLogRow,
    new_id, utcnow,
)
from datetime import timedelta

logger = logging.getLogger("seed")

DEMO_REQUESTER = "requester@example.com"
DEMO_APPROVER = "approver@example.com"


def seed_if_empty():
    """Populate the DB with demo rows. No-op unless ``SEED_DEMO_DATA=true``."""
    if os.getenv("SEED_DEMO_DATA", "false").lower() not in ("1", "true", "yes"):
        logger.info("SEED_DEMO_DATA not enabled - skipping demo seed.")
        return

    db: Session = SessionLocal()
    try:
        if db.query(BlueprintRow).count() > 0:
            logger.info("Database already has data - skipping seed.")
            return

        logger.info("Seeding database with demo data...")
        now = utcnow()

        bp_cs = BlueprintRow(
            id=new_id(), name="Copilot Studio - Customer Service",
            description="Standard blueprint for customer-facing Copilot Studio agents with CRM and knowledge base access.",
            agent_type="copilot_studio", permission_mode="inheritable",
            default_permissions=[
                {"resource": "Microsoft Graph", "scope": "User.Read", "type": "Delegated"},
                {"resource": "Dynamics 365", "scope": "user_impersonation", "type": "Delegated"},
            ],
            required_apis=["Microsoft Graph", "Dynamics 365"],
            created_by=DEMO_REQUESTER,
            created_at=now - timedelta(days=5), status="active",
        )
        bp_foundry = BlueprintRow(
            id=new_id(), name="Azure AI Foundry - Data Pipeline",
            description="Blueprint for AI Foundry agents that process and transform enterprise data across Azure services.",
            agent_type="foundry", permission_mode="manual",
            default_permissions=[
                {"resource": "Azure Storage", "scope": "Storage.Read", "type": "Application"},
                {"resource": "Azure Key Vault", "scope": "Secrets.Get", "type": "Application"},
                {"resource": "Microsoft Graph", "scope": "Files.Read.All", "type": "Application"},
            ],
            required_apis=["Azure Storage", "Azure Key Vault", "Microsoft Graph"],
            created_by=DEMO_REQUESTER,
            created_at=now - timedelta(days=3), status="active",
        )
        bp_custom = BlueprintRow(
            id=new_id(), name="Custom Agent - Security Operations",
            description="Hardened blueprint for custom security agents with Microsoft Sentinel and Defender API access.",
            agent_type="custom", permission_mode="manual",
            default_permissions=[
                {"resource": "Microsoft Graph", "scope": "SecurityEvents.Read.All", "type": "Application"},
                {"resource": "Microsoft Sentinel", "scope": "Incidents.ReadWrite", "type": "Application"},
                {"resource": "Microsoft Defender", "scope": "AdvancedHunting.Read", "type": "Application"},
            ],
            required_apis=["Microsoft Graph", "Microsoft Sentinel", "Microsoft Defender"],
            created_by=DEMO_APPROVER,
            created_at=now - timedelta(days=1), status="active",
        )
        db.add_all([bp_cs, bp_foundry, bp_custom])

        bp_pending = BlueprintRow(
            id=new_id(), name="Copilot Studio - HR Onboarding",
            description="Blueprint for HR onboarding agents with access to employee profiles and onboarding workflows.",
            agent_type="copilot_studio", permission_mode="inheritable",
            default_permissions=[
                {"resource": "Microsoft Graph", "scope": "User.Read.All", "type": "Application"},
                {"resource": "Microsoft Graph", "scope": "People.Read", "type": "Delegated"},
            ],
            required_apis=["Microsoft Graph"],
            created_by=DEMO_REQUESTER,
            created_at=now - timedelta(hours=6), status="pending",
        )
        db.add(bp_pending)

        id_provisioned = IdentityRequestRow(
            id=new_id(), blueprint_id=bp_cs.id,
            display_name="Contoso-CustomerService-Agent-Prod",
            description="Production customer service agent for Contoso tenant.",
            agent_type="copilot_studio", environment="production",
            justification="Required for GA launch of customer service automation.",
            requested_by=DEMO_REQUESTER,
            requested_at=now - timedelta(days=4), status="provisioned",
            approved_by=DEMO_APPROVER,
            approved_at=now - timedelta(days=3),
            provisioned_app_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            provisioned_object_id="12345678-abcd-ef01-2345-678901234567",
        )
        id_pending_1 = IdentityRequestRow(
            id=new_id(), blueprint_id=bp_foundry.id,
            display_name="Woodgrove-DataPipeline-Agent-Dev",
            description="Development data pipeline agent for Woodgrove analytics.",
            agent_type="foundry", environment="dev",
            justification="Needed to prototype new data ingestion pipeline for Q3 analytics.",
            requested_by=DEMO_REQUESTER,
            requested_at=now - timedelta(hours=12), status="pending",
        )
        id_pending_2 = IdentityRequestRow(
            id=new_id(), blueprint_id=bp_custom.id,
            display_name="SecOps-ThreatHunt-Agent-Staging",
            description="Staging security operations agent for automated threat hunting.",
            agent_type="custom", environment="staging",
            justification="Security team needs automated threat hunting for SOC Tier 1 triage.",
            requested_by=DEMO_REQUESTER,
            requested_at=now - timedelta(hours=4), status="pending",
        )
        id_rejected = IdentityRequestRow(
            id=new_id(), blueprint_id=None,
            display_name="Test-Agent-NoBlueprint",
            description="Test identity request without a blueprint.",
            agent_type="custom", environment="dev",
            justification="Testing custom agent flow.",
            requested_by=DEMO_REQUESTER,
            requested_at=now - timedelta(days=2), status="rejected",
            approved_by=DEMO_APPROVER,
            approved_at=now - timedelta(days=1),
            rejection_reason="Custom agents require an approved blueprint. Please create a blueprint first.",
        )
        db.add_all([id_provisioned, id_pending_1, id_pending_2, id_rejected])

        perm_granted = PermissionRequestRow(
            id=new_id(),
            identity_app_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            identity_display_name="Contoso-CustomerService-Agent-Prod",
            requested_permissions=[
                {"resource": "Microsoft Graph", "scope": "Mail.Send", "type": "Application"},
                {"resource": "Microsoft Graph", "scope": "Calendars.Read", "type": "Delegated"},
            ],
            justification="Agent needs to send appointment confirmations and read calendar availability.",
            requested_by=DEMO_REQUESTER,
            requested_at=now - timedelta(days=2), status="granted",
            approved_by=DEMO_APPROVER,
            approved_at=now - timedelta(days=1),
        )
        perm_pending = PermissionRequestRow(
            id=new_id(),
            identity_app_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            identity_display_name="Contoso-CustomerService-Agent-Prod",
            requested_permissions=[
                {"resource": "SharePoint", "scope": "Sites.Read.All", "type": "Application"},
                {"resource": "Microsoft Graph", "scope": "Files.ReadWrite.All", "type": "Application"},
            ],
            justification="Agent needs access to knowledge base articles stored in SharePoint.",
            requested_by=DEMO_REQUESTER,
            requested_at=now - timedelta(hours=2), status="pending",
        )
        db.add_all([perm_granted, perm_pending])

        audit_entries = [
            AuditLogRow(id=new_id(), entity_type="blueprint", entity_id=bp_cs.id,
                action="created", performed_by=DEMO_REQUESTER,
                performed_at=now - timedelta(days=5),
                details={"name": bp_cs.name, "agent_type": "copilot_studio"}),
            AuditLogRow(id=new_id(), entity_type="blueprint", entity_id=bp_cs.id,
                action="approved", performed_by=DEMO_APPROVER,
                performed_at=now - timedelta(days=5),
                details={"name": bp_cs.name, "decision": "approve"}),
            AuditLogRow(id=new_id(), entity_type="blueprint", entity_id=bp_foundry.id,
                action="created", performed_by=DEMO_REQUESTER,
                performed_at=now - timedelta(days=3),
                details={"name": bp_foundry.name, "agent_type": "foundry"}),
            AuditLogRow(id=new_id(), entity_type="blueprint", entity_id=bp_foundry.id,
                action="approved", performed_by=DEMO_APPROVER,
                performed_at=now - timedelta(days=3),
                details={"name": bp_foundry.name, "decision": "approve"}),
            AuditLogRow(id=new_id(), entity_type="blueprint", entity_id=bp_custom.id,
                action="created", performed_by=DEMO_APPROVER,
                performed_at=now - timedelta(days=1),
                details={"name": bp_custom.name, "agent_type": "custom"}),
            AuditLogRow(id=new_id(), entity_type="identity_request", entity_id=id_provisioned.id,
                action="created", performed_by=DEMO_REQUESTER,
                performed_at=now - timedelta(days=4),
                details={"display_name": id_provisioned.display_name, "environment": "production"}),
            AuditLogRow(id=new_id(), entity_type="identity_request", entity_id=id_provisioned.id,
                action="approved", performed_by=DEMO_APPROVER,
                performed_at=now - timedelta(days=3),
                details={"display_name": id_provisioned.display_name, "decision": "approve"}),
            AuditLogRow(id=new_id(), entity_type="identity_request", entity_id=id_provisioned.id,
                action="provisioned", performed_by="system",
                performed_at=now - timedelta(days=3),
                details={"app_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "display_name": id_provisioned.display_name}),
            AuditLogRow(id=new_id(), entity_type="identity_request", entity_id=id_rejected.id,
                action="rejected", performed_by=DEMO_APPROVER,
                performed_at=now - timedelta(days=1),
                details={"display_name": id_rejected.display_name, "reason": id_rejected.rejection_reason}),
            AuditLogRow(id=new_id(), entity_type="permission_request", entity_id=perm_granted.id,
                action="granted", performed_by=DEMO_APPROVER,
                performed_at=now - timedelta(days=1),
                details={"identity": perm_granted.identity_display_name, "permissions": 2}),
            AuditLogRow(id=new_id(), entity_type="blueprint", entity_id=bp_pending.id,
                action="created", performed_by=DEMO_REQUESTER,
                performed_at=now - timedelta(hours=6),
                details={"name": bp_pending.name, "agent_type": "copilot_studio"}),
            AuditLogRow(id=new_id(), entity_type="identity_request", entity_id=id_pending_1.id,
                action="created", performed_by=DEMO_REQUESTER,
                performed_at=now - timedelta(hours=12),
                details={"display_name": id_pending_1.display_name, "environment": "dev"}),
            AuditLogRow(id=new_id(), entity_type="identity_request", entity_id=id_pending_2.id,
                action="created", performed_by=DEMO_REQUESTER,
                performed_at=now - timedelta(hours=4),
                details={"display_name": id_pending_2.display_name, "environment": "staging"}),
            AuditLogRow(id=new_id(), entity_type="permission_request", entity_id=perm_pending.id,
                action="created", performed_by=DEMO_REQUESTER,
                performed_at=now - timedelta(hours=2),
                details={"identity": perm_pending.identity_display_name, "permissions": 2}),
        ]
        db.add_all(audit_entries)
        db.commit()
        logger.info("Seeded: 4 blueprints, 4 identity requests, 2 permission requests, %d audit log entries.", len(audit_entries))
    except Exception as exc:
        logger.error("Seed failed: %s", exc)
        db.rollback()
    finally:
        db.close()
