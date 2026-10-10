from starlette.testclient import TestClient


def test_health_endpoint_success(client: TestClient):
    """Verify GET /health returns HTTP 200 and expected status."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert data["status"] == "ok"


def test_health_endpoint_no_secrets_leaked(client: TestClient):
    """Verify health response contains only safe minimal status without internal paths or keys."""
    response = client.get("/health")
    data = response.json()
    assert list(data.keys()) == ["status"]
    assert "db" not in data
    assert "password" not in data
