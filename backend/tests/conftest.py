"""
Pytest configuration for AegisAI backend tests.

Calls init_db() once before any test runs so that the incidents and
incident_events tables exist.  This is necessary because TestClient(app)
at module level does not trigger the FastAPI lifespan, so the app's own
startup hook never fires during tests.
"""
import pytest
from db import init_db


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    init_db()
