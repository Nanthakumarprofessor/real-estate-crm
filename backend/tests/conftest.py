"""
Pytest configuration and shared fixtures.

Provides:
  - `client`: a TestClient for the FastAPI app (no real DB required for unit tests)
  - `db_session`: a real DB session for integration tests (requires running PostgreSQL)

Phase 1: only the `client` fixture is needed.
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    A synchronous TestClient wrapping the FastAPI application.
    Uses session scope so the app is only created once per test run.
    """
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
