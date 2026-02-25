"""
API tests for AegisAI. Require backend env (e.g. DATABASE_URL when running locally).
Run from backend/: pytest tests/ -v
With Docker Compose up, run: docker compose -f deployment/docker-compose.yml exec backend pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_200_and_status():
    """Health endpoint returns 200 and a status field for operators/orchestration."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "database" in data


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
