"""
Regression tests for ResolveAI Customer Portal Security, Case Events Audit History,
and Operational Analytics Endpoints.
Verifies customer ownership boundaries, anti-IDOR protections, and staff RBAC.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.auth import create_access_token, create_customer_token, hash_password
from app.database.db import get_db, SessionLocal
from app.database.models import Customer, Order, SupportCase, CaseEvent, User


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_customer_verify_access_valid(client, db_session):
    """Customer verifying with registered email and own order number gets session token."""
    # Alice owns ORD-2026-001
    response = client.post(
        "/api/v1/customer/verify-access",
        json={"email": "alice.chen@example.com", "order_number": "ORD-2026-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["customer_email"] == "alice.chen@example.com"
    assert data["token_type"] == "bearer"
    assert isinstance(data["cases"], list)


def test_customer_verify_access_invalid_email(client):
    """Unknown email returns 404 Not Found."""
    response = client.post(
        "/api/v1/customer/verify-access",
        json={"email": "nonexistent.user999@example.com"},
    )
    assert response.status_code == 404
    assert "No registered customer account found" in response.json()["detail"]


def test_customer_verify_access_wrong_order_cross_customer_forbidden(client):
    """Providing another customer's order number is rejected with 403 Forbidden."""
    # Alice trying to claim Bob's order ORD-2026-003
    response = client.post(
        "/api/v1/customer/verify-access",
        json={"email": "alice.chen@example.com", "order_number": "ORD-2026-003"},
    )
    assert response.status_code == 403
    assert "not associated with customer" in response.json()["detail"]


def test_customer_case_detail_authorized(client, db_session):
    """Authenticated customer can view their own case details (sanitized without internal notes)."""
    alice = db_session.scalar(select(Customer).where(Customer.email == "alice.chen@example.com"))
    assert alice is not None

    token = create_customer_token(customer_id=alice.id, email=alice.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/customer/cases/CASE-2026-1001", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["case_number"] == "CASE-2026-1001"
    assert "complaint_text" in data
    assert "status" in data
    # Verify no supervisor notes or staff internal fields leaked
    assert "supervisor_notes" not in data
    assert "reviewer_id" not in data
    assert "hashed_password" not in data


def test_customer_case_detail_unauthorized_cross_customer_access(client, db_session):
    """Customer A cannot view Customer B's case details (anti-IDOR check)."""
    bob = db_session.scalar(select(Customer).where(Customer.email == "bob.martinez@example.com"))
    assert bob is not None

    # Bob's token trying to read Alice's CASE-2026-1001
    token = create_customer_token(customer_id=bob.id, email=bob.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/customer/cases/CASE-2026-1001", headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_customer_case_detail_unauthenticated(client):
    """Unauthenticated request to customer case detail returns 401."""
    response = client.get("/api/v1/customer/cases/CASE-2026-1001")
    assert response.status_code == 401


def test_case_events_read_staff_authorized(client, db_session):
    """Authenticated staff can view case events audit history in chronological order."""
    supervisor = db_session.scalar(select(User).where(User.username == "supervisor_alice"))
    assert supervisor is not None

    token = create_access_token(username=supervisor.username, role=supervisor.role, user_id=supervisor.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/cases/by-number/CASE-2026-1001/events", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
    if data["events"]:
        assert "event_type" in data["events"][0]
        assert "message" in data["events"][0]


def test_case_events_read_unauthenticated(client):
    """Unauthenticated access to audit history returns 401."""
    response = client.get("/api/v1/cases/by-number/CASE-2026-1001/events")
    assert response.status_code == 401


def test_analytics_overview_staff_authorized(client, db_session):
    """Authenticated staff can view operational analytics computed from real database."""
    supervisor = db_session.scalar(select(User).where(User.username == "supervisor_alice"))
    assert supervisor is not None

    token = create_access_token(username=supervisor.username, role=supervisor.role, user_id=supervisor.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/analytics/overview", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_cases"] >= 1
    assert "open_cases" in data
    assert "pending_approvals" in data
    assert "category_distribution" in data
    assert "status_distribution" in data


def test_analytics_overview_unauthenticated(client):
    """Unauthenticated access to analytics endpoint returns 401."""
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 401
