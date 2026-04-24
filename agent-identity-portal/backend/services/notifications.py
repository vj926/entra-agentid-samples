"""Notification services — email + Teams Adaptive Cards."""

from __future__ import annotations
import asyncio
import html
import logging
import aiosmtplib
import httpx
from email.message import EmailMessage
from config import settings

logger = logging.getLogger("notifications")


async def notify_new_request(
    request_id: str,
    request_type: str,
    display_name: str,
):
    """Send notifications to approvers via all configured channels."""
    tasks = []

    if settings.smtp_username:
        tasks.append(_send_email_notification(request_id, request_type, display_name))
    if settings.teams_webhook_url:
        tasks.append(_send_teams_card(request_id, request_type, display_name))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    else:
        logger.info("New %s request: %s (id=%s)", request_type, display_name, request_id)


# ── Email notification ──────────────────────────────────────────

async def _send_email_notification(
    request_id: str,
    request_type: str,
    display_name: str,
):
    type_label = "Agent Identity" if request_type == "identity_request" else "Permission"
    approval_url = f"{settings.approval_link_base_url}/admin/approvals"

    msg = EmailMessage()
    msg["From"] = settings.smtp_username
    msg["To"] = settings.smtp_username  # In production, send to approver group
    msg["Subject"] = f"[Action Required] New {type_label} Request: {display_name}"
    msg.set_content(
        f"A new {type_label.lower()} request has been submitted.\n\n"
        f"Name: {display_name}\n"
        f"Request ID: {request_id}\n\n"
        f"Review and approve/reject at:\n{approval_url}\n"
    )

    safe_name = html.escape(display_name)
    email_html = f"""
    <html><body style="font-family: Segoe UI, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background: #0078d4; color: white; padding: 16px 24px;">
            <h2 style="margin: 0;">New {type_label} Request</h2>
        </div>
        <div style="padding: 24px;">
            <p>A new request requires your approval:</p>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 8px; font-weight: bold;">Name</td><td style="padding: 8px;">{safe_name}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Type</td><td style="padding: 8px;">{type_label}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Request ID</td><td style="padding: 8px; font-family: monospace;">{request_id}</td></tr>
            </table>
            <div style="margin-top: 24px; text-align: center;">
                <a href="{approval_url}" style="background: #0078d4; color: white; padding: 12px 32px; text-decoration: none; border-radius: 4px; display: inline-block;">
                    Review Request
                </a>
            </div>
        </div>
    </div>
    </body></html>
    """
    msg.add_alternative(email_html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("Sent email notification for %s", request_id)
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)


# ── Teams Adaptive Card ─────────────────────────────────────────

async def _send_teams_card(
    request_id: str,
    request_type: str,
    display_name: str,
):
    type_label = "Agent Identity" if request_type == "identity_request" else "Permission"
    approval_url = f"{settings.approval_link_base_url}/admin/approvals"

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"New {type_label} Request",
                            "size": "Large",
                            "weight": "Bolder",
                            "color": "Accent",
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Name", "value": display_name},
                                {"title": "Type", "value": type_label},
                                {"title": "Request ID", "value": request_id},
                                {"title": "Status", "value": "Pending Approval"},
                            ],
                        },
                        {
                            "type": "TextBlock",
                            "text": "This request requires your review and approval.",
                            "wrap": True,
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "Review in Portal",
                            "url": approval_url,
                            "style": "positive",
                        },
                    ],
                },
            }
        ],
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.teams_webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        logger.info("Sent Teams card for %s", request_id)
    except Exception as exc:
        logger.error("Failed to send Teams card: %s", exc)
