"""
AI-powered runbook generation for AegisAI incidents.

Uses Claude when ANTHROPIC_API_KEY is set; falls back to a structured
rule-based runbook otherwise.
"""

from __future__ import annotations

import os

from schemas import Incident


def generate(incident: Incident) -> str:
    """Generate a step-by-step remediation runbook for an incident."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=(
                    "You are an experienced SRE. Given an incident, produce a concise "
                    "remediation runbook with four numbered sections: "
                    "1) Immediate Mitigation, 2) Root Cause Investigation, "
                    "3) Resolution Steps, 4) Prevention. "
                    "Be specific and actionable. Keep each step to one line."
                ),
                messages=[{
                    "role": "user",
                    "content": (
                        f"Incident: {incident.title}\n"
                        f"Severity: {incident.severity}\n"
                        f"Tenant: {incident.tenant}\n"
                        f"Source: {incident.source}\n"
                        f"Raw log:\n{incident.raw_log}"
                    ),
                }],
            )
            return response.content[0].text
        except Exception as e:
            import logging
            logging.error(f"Claude API error (runbook): {e}")

    return _rule_based(incident)


def _rule_based(incident: Incident) -> str:
    sev = (incident.severity or "unknown").lower()
    is_critical = sev in ("high", "critical")

    lines = [
        f"# Runbook: {incident.title}",
        f"Severity: {sev.upper()}  |  Tenant: {incident.tenant}  |  Source: {incident.source}",
        "",
        "## 1. Immediate Mitigation",
        "1. Confirm the incident is still active — check current error rates.",
        "2. Identify blast radius: which tenants and services are affected.",
        "3. Alert the on-call engineer if not already paged.",
    ]

    if is_critical:
        lines += [
            "4. Consider rolling back the most recent deployment.",
            "5. Enable maintenance mode if user-facing impact is confirmed.",
        ]

    lines += [
        "",
        "## 2. Root Cause Investigation",
        "6. Pull logs from the time window around `created_at`.",
        "7. Check infrastructure metrics: CPU, memory, disk I/O, network.",
        "8. Review recent config, code, or infra changes (last 24h).",
        "9. Inspect dependent service health (databases, queues, third-party APIs).",
        "",
        "## 3. Resolution Steps",
        "10. Apply fix based on root cause found above.",
        "11. Monitor error rates for at least 5 minutes post-fix.",
        "12. Mark incident as 'resolved' once confirmed stable.",
        "",
        "## 4. Prevention",
        "13. Add or update an alert for this failure mode.",
        "14. Write a post-mortem if severity was HIGH or CRITICAL.",
        "15. Create a ticket for any permanent hardening work identified.",
    ]

    return "\n".join(lines)
