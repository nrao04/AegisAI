"""In-memory store for incidents (Phase 2). Replaced by PostgreSQL in Phase 3."""

from typing import List
from schemas import Incident

incidents: List[Incident] = []


def add_incident(incident: Incident) -> None:
    incidents.append(incident)


def get_all_incidents() -> List[Incident]:
    return list(incidents)
