"""
Integration tests for ResolveAI Level 4 FastAPI Workflow Orchestration Endpoint.
Validates POST /api/v1/workflows/resolve, schema validation, and backward compatibility.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_workflow_resolve_valid_order():
    """Verify that POST /api/v1/workflows/resolve executes workflow and returns HTTP 200."""
    payload = {
        "complaint_text": "I received order ORD-2026-001 with damaged product packaging and scratches.",
        "order_number": "ORD-2026-001",
        "category": "electronics",
        "seller_id": "SELLER-001",
    }
    response = client.post("/api/v1/workflows/resolve", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "workflow_id" in data
    assert data["workflow_id"].startswith("wf-")
    assert data["status"] in ("completed", "needs_review", "needs_information")
    assert data["complaint_analysis"] is not None
    assert data["complaint_analysis"]["category"] == "damaged_product"
    assert data["order_investigation"]["order_exists"] is True
    assert data["policy_evidence"] is not None
    assert data["recommended_resolution"] is not None
    assert data["verification_result"] is not None


def test_api_workflow_resolve_missing_order():
    """Verify that an unknown order routes to needs_information with HTTP 200."""
    payload = {
        "complaint_text": "Where is my order ORD-9999-NOTFOUND? It never arrived.",
        "order_number": "ORD-9999-NOTFOUND",
    }
    response = client.post("/api/v1/workflows/resolve", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "needs_information"
    assert data["order_investigation"]["order_exists"] is False
    assert len(data["missing_information"]) > 0


def test_api_workflow_resolve_empty_complaint_validation_error():
    """Verify that empty complaint text is rejected with HTTP 422 Unprocessable Entity."""
    payload = {
        "complaint_text": "   ",
        "order_number": "ORD-2026-001",
    }
    response = client.post("/api/v1/workflows/resolve", json=payload)
    assert response.status_code == 422


def test_api_workflow_backward_compatibility():
    """Verify that existing Level 1, 2, and 3 endpoints remain fully functional."""
    # Status endpoint
    status_resp = client.get("/api/v1/status")
    assert status_resp.status_code == 200

    # Policy search endpoint
    search_resp = client.post(
        "/api/v1/search-policies",
        json={"query": "return window 30 days replacement"},
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["found_relevant"] is True
