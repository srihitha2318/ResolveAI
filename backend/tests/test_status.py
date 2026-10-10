from unittest.mock import patch
from starlette.testclient import TestClient
from app.core.config import settings


def test_status_endpoint_success(client: TestClient):
    """Verify GET /api/v1/status returns 200 and operational subsystem info."""
    response = client.get(f"{settings.API_PREFIX}/status")
    assert response.status_code == 200

    data = response.json()
    assert data["app_name"] == settings.APP_NAME
    assert data["version"] == settings.APP_VERSION
    assert data["environment"] == settings.APP_ENV
    assert data["database"] == "connected"
    assert "subsystems operational" in data["message"].lower()


def test_status_endpoint_database_failure(client: TestClient):
    """Verify GET /api/v1/status reports failure when database connectivity check fails."""
    with patch("app.api.routes.check_db_connection", return_value=False):
        response = client.get(f"{settings.API_PREFIX}/status")
        assert response.status_code == 503

        data = response.json()
        assert data["database"] == "disconnected"
        assert "failure" in data["message"].lower()


def test_root_endpoint_metadata(client: TestClient):
    """Verify GET / returns documentation links and operational hints."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["app"] == settings.APP_NAME
    assert "/docs" in data["docs"]
    assert f"{settings.API_PREFIX}/status" in data["api_status"]
