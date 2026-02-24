"""
PostgreSQL access layer for incidents (Phase 3).

Uses a simple synchronous psycopg2 connection created on demand.
The connection string is read from the environment variable
`DATABASE_URL`, e.g.:

  export DATABASE_URL="postgresql://user:password@localhost:5432/aegisai"

This module is intentionally minimal and can be evolved into a
connection pool or async layer later.
"""

import os
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from schemas import Incident


def _get_conn():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Example: postgresql://user:password@localhost:5432/aegisai"
        )
    return psycopg2.connect(database_url)


def init_db() -> None:
    """Create incidents table if it does not exist."""
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS incidents (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        source TEXT NOT NULL,
                        raw_log TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        status TEXT NOT NULL
                    );
                    """
                )
    finally:
        conn.close()


def insert_incident(incident: Incident) -> None:
    """Insert a single incident row."""
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO incidents (
                        id, title, severity, source, raw_log, created_at, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        incident.id,
                        incident.title,
                        incident.severity,
                        incident.source,
                        incident.raw_log,
                        incident.created_at,
                        incident.status,
                    ),
                )
    finally:
        conn.close()


def get_incident(id: str) -> Optional[Incident]:
    """Fetch a single incident by ID."""
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM incidents WHERE id = %s", (id,))
                row = cur.fetchone()
                if not row:
                    return None
                return Incident(**row)
    finally:
        conn.close()


def get_incidents(limit: int = 100) -> list[Incident]:
    """Fetch up to `limit` most recent incidents."""
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM incidents
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                return [Incident(**row) for row in rows]
    finally:
        conn.close()

