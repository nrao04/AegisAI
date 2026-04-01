"""
PostgreSQL access layer for incidents.

Uses a ThreadedConnectionPool (min=2, max=10) to avoid the overhead of
opening a new TCP connection on every request.  The pool is initialised
lazily behind a lock so it is safe under concurrent FastAPI/uvicorn workers.

Environment variable:
  DATABASE_URL  e.g. postgresql://user:password@localhost:5432/aegisai
"""

import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor

from schemas import Incident


_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                database_url = os.getenv("DATABASE_URL")
                if not database_url:
                    raise RuntimeError(
                        "DATABASE_URL environment variable is not set. "
                        "Example: postgresql://user:password@localhost:5432/aegisai"
                    )
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2, maxconn=10, dsn=database_url
                )
    return _pool


@contextmanager
def _get_conn():
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def init_db() -> None:
    """Create incidents table, events table, and indexes if they do not exist."""
    with _get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                # ── Incidents table ──────────────────────────────────────────
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS incidents (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        source TEXT NOT NULL,
                        tenant TEXT NOT NULL DEFAULT 'default',
                        raw_log TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        status TEXT NOT NULL
                    );
                    """
                )
                # Backwards-compat: add tenant column if missing
                cur.execute(
                    """
                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'incidents' AND column_name = 'tenant'
                        ) THEN
                            ALTER TABLE incidents ADD COLUMN tenant TEXT NOT NULL DEFAULT 'default';
                        END IF;
                    END $$
                    """
                )
                # Index for ORDER BY created_at DESC
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS incidents_created_at_idx
                    ON incidents (created_at DESC);
                    """
                )

                # ── Incident events table (audit trail + runbooks) ───────────
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS incident_events (
                        id SERIAL PRIMARY KEY,
                        incident_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        note TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS events_inc_idx
                    ON incident_events (incident_id, created_at DESC);
                    """
                )


# ── Incidents CRUD ────────────────────────────────────────────────────────────

def insert_incident(incident: Incident) -> None:
    """Upsert a single incident row (idempotent on id)."""
    with _get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO incidents (
                        id, title, severity, source, tenant, raw_log, created_at, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title      = EXCLUDED.title,
                        severity   = EXCLUDED.severity,
                        source     = EXCLUDED.source,
                        tenant     = EXCLUDED.tenant,
                        raw_log    = EXCLUDED.raw_log,
                        created_at = EXCLUDED.created_at,
                        status     = EXCLUDED.status;
                    """,
                    (
                        incident.id,
                        incident.title,
                        incident.severity,
                        incident.source,
                        getattr(incident, "tenant", "default"),
                        incident.raw_log,
                        incident.created_at,
                        incident.status,
                    ),
                )


def get_incident(id: str) -> Optional[Incident]:
    """Fetch a single incident by ID."""
    with _get_conn() as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM incidents WHERE id = %s", (id,))
                row = cur.fetchone()
                return Incident(**row) if row else None


def get_incidents(limit: int = 100) -> list[Incident]:
    """Fetch up to `limit` most recent incidents."""
    with _get_conn() as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM incidents ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                return [Incident(**row) for row in cur.fetchall()]


def check_duplicate(title: str, source: str, window_minutes: int = 5) -> bool:
    """Return True if an OPEN incident with the same title+source exists within the window."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    with _get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM incidents
                    WHERE title = %s AND source = %s
                      AND status = 'open'
                      AND created_at > %s
                    LIMIT 1
                    """,
                    (title, source, cutoff),
                )
                return cur.fetchone() is not None


# ── Incident events (audit trail) ─────────────────────────────────────────────

def log_event(incident_id: str, event_type: str, note: str = "") -> None:
    """Append an event to the audit trail for an incident."""
    with _get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO incident_events (incident_id, event_type, note)
                    VALUES (%s, %s, %s)
                    """,
                    (incident_id, event_type, note or ""),
                )


def get_events(incident_id: str) -> list[dict]:
    """Return all events for an incident, oldest first."""
    with _get_conn() as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT event_type, note, created_at
                    FROM incident_events
                    WHERE incident_id = %s
                    ORDER BY created_at ASC
                    """,
                    (incident_id,),
                )
                return [dict(row) for row in cur.fetchall()]


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Return all-time operational stats."""
    with _get_conn() as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*)                                                             AS total,
                        COUNT(*) FILTER (WHERE status = 'open')                             AS open_count,
                        COUNT(*) FILTER (WHERE status = 'resolved')                         AS resolved,
                        COUNT(*) FILTER (WHERE severity IN ('high','critical')
                                          AND status = 'open')                              AS high_open,
                        COUNT(*) FILTER (WHERE severity = 'medium' AND status = 'open')     AS medium_open
                    FROM incidents
                    """
                )
                row = cur.fetchone()
                return dict(row) if row else {}
