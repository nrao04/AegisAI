"""
Slack / generic webhook notifications for AegisAI.

Set SLACK_WEBHOOK_URL in the environment to enable notifications.
Only HIGH and CRITICAL incidents trigger new-incident alerts.
Resolution of any high/critical incident also fires a notification.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request

from schemas import Incident

logger = logging.getLogger(__name__)

_SEV_EMOJI = {
    "critical": "🚨",
    "high":     "🔴",
    "medium":   "🟡",
    "low":      "🟢",
}


def _webhook_url() -> str | None:
    return os.getenv("SLACK_WEBHOOK_URL") or None


def notify_new_incident(incident: Incident) -> None:
    """Fire a Slack alert for new HIGH / CRITICAL incidents."""
    url = _webhook_url()
    if not url:
        return

    sev = (incident.severity or "").lower()
    if sev not in ("high", "critical"):
        return

    emoji = _SEV_EMOJI.get(sev, "⚪")
    log_preview = (incident.raw_log or "")[:300]

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {sev.upper()} Incident Detected",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Title:*\n{incident.title}"},
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{incident.tenant}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{incident.severity}"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{incident.source}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Log preview:*\n```{log_preview}```",
                },
            },
        ]
    }
    _post(url, payload)


def notify_resolved(incident: Incident) -> None:
    """Notify when a HIGH / CRITICAL incident is resolved."""
    url = _webhook_url()
    if not url:
        return

    sev = (incident.severity or "").lower()
    if sev not in ("high", "critical"):
        return

    _post(url, {
        "text": (
            f"✅ *{sev.upper()}* incident resolved: *{incident.title}* "
            f"(tenant: {incident.tenant})"
        )
    })


def _post(url: str, payload: dict) -> None:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info("Slack notification sent (status=%s)", resp.status)
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)
