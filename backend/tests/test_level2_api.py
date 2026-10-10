from starlette.testclient import TestClient
from sqlalchemy.orm import Session
from app.database.seed import seed_database
from app.core.config import settings


def test_api_analyze_complaint(client: TestClient):
    """Test POST /api/v1/analyze-complaint endpoint."""
    response = client.post(
        f"{settings.API_PREFIX}/analyze-complaint",
        json={"complaint_text": "My package ORD-2026-001 has broken parts.", "order_number": None},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "damaged_product"
    assert data["order_number"] == "ORD-2026-001"
    assert data["image_relevant"] is True


def test_api_investigate_order_success(client: TestClient, test_db: Session):
    """Test POST /api/v1/investigate-order for existing seeded order."""
    seed_database(test_db)
    response = client.post(
        f"{settings.API_PREFIX}/investigate-order",
        json={"order_number": "ORD-2026-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["order_exists"] is True
    assert data["order_number"] == "ORD-2026-001"
    assert data["order_details"]["product_name"] == "Ergonomic Office Chair"


def test_api_search_policies(client: TestClient):
    """Test POST /api/v1/search-policies returns relevant passages."""
    response = client.post(
        f"{settings.API_PREFIX}/search-policies",
        json={"query": "return window 30 days"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["found_relevant"] is True
    assert len(data["passages"]) > 0


def test_api_recommend_resolution(client: TestClient):
    """Test POST /api/v1/recommend-resolution endpoint."""
    payload = {
        "complaint_analysis": {
            "category": "damaged_product",
            "main_issue": "Broken port",
            "desired_outcome": "Replacement",
            "order_number": "ORD-2026-005",
            "image_relevant": True,
            "additional_info_required": False,
            "analysis_method": "rule_based",
        },
        "order_investigation": {
            "order_exists": True,
            "order_number": "ORD-2026-005",
            "order_details": {
                "id": 5,
                "order_number": "ORD-2026-005",
                "product_name": "Docking Station",
                "order_status": "delivered",
                "delivery_status": "delivered",
                "total_amount": 499900,
                "currency": "INR",
                "customer_id": 3,
            },
            "refund_status": "not_recorded",
            "limitations": "None",
        },
        "policy_evidence": {
            "query": "damaged",
            "passages": [
                {
                    "document_name": "return_policy.md",
                    "passage": "Damaged goods eligible for replacement.",
                }
            ],
            "found_relevant": True,
            "retrieval_method": "keyword_search",
            "explanation": "Policy match",
        },
    }
    response = client.post(f"{settings.API_PREFIX}/recommend-resolution", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation_type"] == "recommend_replacement_review"


def test_api_verify_resolution(client: TestClient):
    """Test POST /api/v1/verify-resolution endpoint."""
    payload = {
        "recommendation": {
            "recommendation_type": "explain_order_status",
            "title": "Delivery status",
            "reasoning": "Standard update",
            "action_required": "Provide tracking",
            "human_approval_required": False,
            "missing_information": [],
            "evidence_used": [],
            "method": "rule_based",
        }
    }
    response = client.post(f"{settings.API_PREFIX}/verify-resolution", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verification_status"] == "pass"
    assert data["is_valid"] is True


def test_api_get_order_details(client: TestClient, test_db: Session):
    """Test GET /api/v1/orders/{order_number} for 200 and 404."""
    seed_database(test_db)
    # Existing
    resp = client.get(f"{settings.API_PREFIX}/orders/ORD-2026-001")
    assert resp.status_code == 200
    assert resp.json()["order_number"] == "ORD-2026-001"

    # Not found
    resp404 = client.get(f"{settings.API_PREFIX}/orders/ORD-NONEXISTENT")
    assert resp404.status_code == 404


def test_api_get_case_details(client: TestClient, test_db: Session):
    """Test GET /api/v1/cases/{case_number} for 200 and 404."""
    seed_database(test_db)
    # Existing
    resp = client.get(f"{settings.API_PREFIX}/cases/CASE-2026-1001")
    assert resp.status_code == 200
    assert resp.json()["case_number"] == "CASE-2026-1001"

    # Not found
    resp404 = client.get(f"{settings.API_PREFIX}/cases/CASE-UNKNOWN")
    assert resp404.status_code == 404


def test_api_create_case_ticket_and_event(client: TestClient, test_db: Session):
    """Test creating ticket and event via operational API endpoints."""
    seed_database(test_db)

    # 1. Create ticket
    ticket_resp = client.post(
        f"{settings.API_PREFIX}/cases/1/tickets",
        json={"category": "api_test_ticket"},
    )
    assert ticket_resp.status_code == 201
    assert ticket_resp.json()["category"] == "api_test_ticket"

    # 2. Non-existent case ticket
    ticket_404 = client.post(
        f"{settings.API_PREFIX}/cases/99999/tickets",
        json={"category": "api_test_ticket"},
    )
    assert ticket_404.status_code == 404

    # 3. Create event
    event_resp = client.post(
        f"{settings.API_PREFIX}/cases/1/events",
        json={"event_type": "api_audit", "message": "API audit check performed"},
    )
    assert event_resp.status_code == 201
    assert event_resp.json()["event_type"] == "api_audit"


def test_api_backward_compatibility(client: TestClient):
    """Ensure Level 1 health and status probes remain 100% operational."""
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json() == {"status": "ok"}

    status_resp = client.get(f"{settings.API_PREFIX}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["database"] == "connected"
