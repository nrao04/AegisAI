"""
Chatbot service for AegisAI.

Rule-based by default. If ANTHROPIC_API_KEY is set, uses Claude for
richer, context-aware responses.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import List

from db import get_incidents
from schemas import Incident


def _build_context(incidents: List[Incident]) -> str:
    """Build a structured summary of current incidents for LLM context."""
    if not incidents:
        return "No recent incidents."

    severities = Counter(i.severity or "unknown" for i in incidents)
    statuses = Counter(i.status or "unknown" for i in incidents)
    tenants = Counter(i.tenant or "default" for i in incidents)

    lines = [f"Total incidents: {len(incidents)}"]
    lines.append("By severity: " + ", ".join(f"{c} {s}" for s, c in severities.most_common()))
    lines.append("By status: " + ", ".join(f"{c} {s}" for s, c in statuses.most_common()))
    lines.append("By tenant: " + ", ".join(f"{c} {t}" for t, c in tenants.most_common()))
    lines.append("\nRecent incidents:")
    for inc in incidents[:10]:
        lines.append(f"- [{inc.tenant}] [{inc.severity}/{inc.status}] {inc.title}")
    return "\n".join(lines)


def _summarize_rule_based(incidents: List[Incident]) -> str:
    if not incidents:
        return "No recent incidents found."

    severities = Counter(i.severity or "unknown" for i in incidents)
    statuses = Counter(i.status or "unknown" for i in incidents)
    tenants = Counter(i.tenant or "default" for i in incidents)

    lines = [f"I see {len(incidents)} recent incident(s)."]
    lines.append("By severity: " + ", ".join(f"{c} {s}" for s, c in severities.most_common()) + ".")
    lines.append("By status: " + ", ".join(f"{c} {s}" for s, c in statuses.most_common()) + ".")
    lines.append("By tenant: " + ", ".join(f"{c} {t}" for t, c in tenants.most_common()) + ".")

    examples = incidents[:3]
    if examples:
        lines.append("Examples:")
        for inc in examples:
            lines.append(f"- [{inc.tenant}] [{inc.severity}/{inc.status}] {inc.title}")

    return "\n".join(lines)


def answer(question: str, limit: int = 50) -> str:
    """Answer an incident-related question. Uses Claude if ANTHROPIC_API_KEY is set."""
    incidents = get_incidents(limit=limit)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            context = _build_context(incidents)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=(
                    "You are AegisAI, an incident response assistant. "
                    "Answer in plain text only — no markdown, no headers, no bullet symbols, no emojis, no tables. "
                    "Be direct and concise: 3 to 6 lines maximum. "
                    "Prioritize open high-severity incidents. "
                    "Current system state:\n\n"
                    + context
                ),
                messages=[{"role": "user", "content": question}],
            )
            return response.content[0].text
        except Exception as e:
            import logging
            logging.error(f"Claude API error (chatbot): {e}")

    # Rule-based fallback
    q = question.strip().lower()
    if any(kw in q for kw in ("what's broken", "whats broken", "what is broken", "incidents", "status")):
        return _summarize_rule_based(incidents)
    return (
        "I can help summarize recent incidents. "
        'Try asking: "what\'s broken right now?"'
    )
