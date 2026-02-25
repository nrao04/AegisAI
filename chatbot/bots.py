"""
Simple chatbot layer for AegisAI (Phase 7).

Given a high-level question like "what's broken?", this module:
  - Calls the AegisAI incidents API
  - Aggregates incidents by severity and status
  - Returns a human-friendly summary

This is intentionally rule-based and dependency-light; it can be
extended later to call an LLM for richer analysis.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections import Counter
from typing import Any, Dict, List


API_BASE = os.getenv("AEGIS_API_BASE", "http://localhost:8000")


def _fetch_incidents(limit: int = 50) -> List[Dict[str, Any]]:
    url = f"{API_BASE}/incidents?limit={limit}"
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def summarize_incidents(limit: int = 50) -> str:
    """
    Fetch recent incidents and return a human-readable summary.

    Example usage:
      python -m chatbot.bots
    """
    incidents = _fetch_incidents(limit=limit)
    if not incidents:
        return "No recent incidents found."

    severities = Counter(i.get("severity", "unknown") for i in incidents)
    statuses = Counter(i.get("status", "unknown") for i in incidents)
    tenants = Counter(i.get("tenant", "default") for i in incidents)

    lines = []
    total = len(incidents)
    lines.append(f"I see {total} recent incident(s).")

    if severities:
        sev_parts = [f"{count} {sev}" for sev, count in severities.most_common()]
        lines.append("By severity: " + ", ".join(sev_parts) + ".")

    if statuses:
        status_parts = [f"{count} {status}" for status, count in statuses.most_common()]
        lines.append("By status: " + ", ".join(status_parts) + ".")

    if tenants:
        tenant_parts = [f"{count} {t}" for t, count in tenants.most_common()]
        lines.append("By tenant: " + ", ".join(tenant_parts) + ".")

    # Highlight a few example incidents.
    examples = incidents[:3]
    if examples:
        lines.append("Examples:")
        for inc in examples:
            title = inc.get("title") or "(no title)"
            tenant = inc.get("tenant", "default")
            sev = inc.get("severity", "unknown")
            status = inc.get("status", "unknown")
            lines.append(f"- [{tenant}] [{sev}/{status}] {title}")

    return "\n".join(lines)


def answer(question: str) -> str:
    """Very small 'chatbot' interface for now."""
    q = question.strip().lower()
    if "what's broken" in q or "whats broken" in q or "what is broken" in q:
        return summarize_incidents()
    if "incidents" in q or "status" in q:
        return summarize_incidents()
    return (
        "I can help summarize recent incidents. "
        "Try asking: \"what's broken right now?\""
    )


if __name__ == "__main__":
    # Basic CLI for manual testing.
    print("AegisAI chatbot. Ask a question, or Ctrl+C to exit.")
    try:
        while True:
            q = input("> ")
            print(answer(q))
    except KeyboardInterrupt:
        print("\nGoodbye.")

