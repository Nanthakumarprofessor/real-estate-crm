"""
Tests for the /api/health endpoint.

These tests do NOT require a database connection.
The health endpoint reports database status but does not fail
if the database is unavailable — it just returns "unavailable".
"""
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """GET /api/health"""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint must always return HTTP 200."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_has_status_ok(self, client: TestClient) -> None:
        """The `status` field must be 'ok'."""
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_response_has_database_field(self, client: TestClient) -> None:
        """The `database` field must be present with a known value."""
        response = client.get("/api/health")
        data = response.json()
        assert "database" in data
        assert data["database"] in ("ok", "unavailable")

    def test_health_response_has_environment_field(self, client: TestClient) -> None:
        """The `environment` field must be present."""
        response = client.get("/api/health")
        data = response.json()
        assert "environment" in data
        assert isinstance(data["environment"], str)

    def test_health_response_shape(self, client: TestClient) -> None:
        """Response must contain exactly the documented fields."""
        response = client.get("/api/health")
        data = response.json()
        assert set(data.keys()) == {"status", "database", "environment"}

    def test_swagger_docs_accessible(self, client: TestClient) -> None:
        """Swagger UI must be available at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_accessible(self, client: TestClient) -> None:
        """OpenAPI JSON schema must be available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Real Estate CRM"
