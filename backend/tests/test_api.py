"""
API tests for AegisAI. Require backend env (e.g. DATABASE_URL when running locally).
Run from backend/: pytest tests/ -v
With Docker Compose up, run: docker compose -f deployment/docker-compose.yml exec backend pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Health & basic ─────────────────────────────────────────────────────────────

def test_health_returns_200_and_status():
    """Health endpoint returns 200 and a status field for operators/orchestration."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "database" in data


def test_root_returns_welcome():
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


# ── Incidents list ─────────────────────────────────────────────────────────────

def test_list_incidents_returns_200_and_list():
    """GET /incidents returns 200 and a JSON list (possibly empty)."""
    r = client.get("/incidents")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_list_incidents_respects_limit():
    """GET /incidents?limit=1 returns at most one item."""
    r = client.get("/incidents?limit=1")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 1


def test_list_incidents_invalid_limit_returns_400():
    """GET /incidents?limit=0 returns 400."""
    r = client.get("/incidents?limit=0")
    assert r.status_code == 400


# ── Single incident ────────────────────────────────────────────────────────────

def test_get_incident_not_found():
    r = client.get("/incidents/nonexistent-id-abc123")
    assert r.status_code == 404
    assert r.json()["detail"] == "Incident not found"


# ── HTTP ingest ────────────────────────────────────────────────────────────────

def test_ingest_creates_incident():
    """POST /ingest creates and returns an incident with expected fields."""
    r = client.post("/ingest", json={"log": "test error: disk full on /dev/sda1", "source": "test"})
    assert r.status_code == 200
    data = r.json()
    assert data["title"]
    assert data["severity"] in ("high", "medium", "low", "critical")
    assert data["source"] == "test"
    assert data["status"] == "open"
    assert "id" in data


def test_ingest_missing_log_returns_422():
    r = client.post("/ingest", json={"source": "test"})
    assert r.status_code == 422


def test_ingest_tenant_from_log():
    """Tenant embedded in log line is extracted correctly."""
    r = client.post("/ingest", json={"log": "CRITICAL: tenant=acme database unreachable"})
    assert r.status_code == 200
    assert r.json()["tenant"] == "acme"


def test_ingest_error_keyword_sets_high_severity():
    r = client.post("/ingest", json={"log": "error: connection refused", "source": "test-sev"})
    assert r.status_code == 200
    assert r.json()["severity"] == "high"


# ── Status update ──────────────────────────────────────────────────────────────

def test_patch_incident_not_found():
    r = client.patch("/incidents/nonexistent-id", json={"status": "resolved"})
    assert r.status_code == 404


def test_patch_incident_status_cycle():
    """Create via ingest then acknowledge and resolve it."""
    create = client.post("/ingest", json={"log": "warn: memory pressure detected", "source": "patch-test"})
    assert create.status_code == 200
    inc_id = create.json()["id"]

    ack = client.patch(f"/incidents/{inc_id}", json={"status": "acknowledged"})
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"

    resolve = client.patch(f"/incidents/{inc_id}", json={"status": "resolved"})
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"


# ── Stats ──────────────────────────────────────────────────────────────────────

def test_stats_returns_expected_keys():
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    for key in ("total_24h", "open_count", "resolved_24h", "high_open", "medium_open"):
        assert key in data, f"Missing key: {key}"


# ── Events / audit trail ───────────────────────────────────────────────────────

def test_events_not_found():
    r = client.get("/incidents/nonexistent-id/events")
    assert r.status_code == 404


def test_events_logged_on_ingest():
    """Creating an incident via /ingest should log a 'created' event."""
    create = client.post("/ingest", json={"log": "info: deploy started", "source": "events-test"})
    assert create.status_code == 200
    inc_id = create.json()["id"]

    r = client.get(f"/incidents/{inc_id}/events")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) >= 1
    assert any(e["event_type"] == "created" for e in events)


def test_events_logged_on_status_change():
    create = client.post("/ingest", json={"log": "warn: high cpu utilization", "source": "events-patch"})
    inc_id = create.json()["id"]

    client.patch(f"/incidents/{inc_id}", json={"status": "acknowledged"})

    r = client.get(f"/incidents/{inc_id}/events")
    events = r.json()
    assert any(e["event_type"] == "status_change" for e in events)


# ── Runbook ────────────────────────────────────────────────────────────────────

def test_runbook_not_found():
    r = client.post("/incidents/nonexistent-id/runbook")
    assert r.status_code == 404


def test_get_runbook_not_found_before_generation():
    """GET /runbook before any generation returns 404."""
    create = client.post("/ingest", json={"log": "error: service crashed", "source": "runbook-test"})
    inc_id = create.json()["id"]

    r = client.get(f"/incidents/{inc_id}/runbook")
    assert r.status_code == 404


def test_generate_runbook_returns_text():
    """POST /runbook returns a non-empty runbook string."""
    create = client.post("/ingest", json={"log": "error: out of memory on node-1", "source": "runbook-gen"})
    inc_id = create.json()["id"]

    r = client.post(f"/incidents/{inc_id}/runbook")
    assert r.status_code == 200
    data = r.json()
    assert "runbook" in data
    assert len(data["runbook"]) > 10


def test_get_runbook_after_generation():
    """GET /runbook after POST returns the stored runbook."""
    create = client.post("/ingest", json={"log": "error: disk quota exceeded", "source": "runbook-get"})
    inc_id = create.json()["id"]

    client.post(f"/incidents/{inc_id}/runbook")

    r = client.get(f"/incidents/{inc_id}/runbook")
    assert r.status_code == 200
    assert "runbook" in r.json()


# ── Chat ───────────────────────────────────────────────────────────────────────

def test_chat_returns_answer():
    r = client.post("/chat", json={"question": "what is the current incident status?"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_chat_empty_question_returns_422():
    r = client.post("/chat", json={"question": ""})
    assert r.status_code == 422
