"""
Integration and unit tests for ResolveAI Level 6 Phase 1: Authentication and RBAC.

Covers:
1. Login with valid credentials (agent, tier 2 supervisor, senior supervisor).
2. Login failures: wrong password, unknown user, inactive user.
3. GET /api/v1/auth/me: valid token, missing token, invalid/tampered token, expired token.
4. RBAC approval enforcement:
   - Frontline agent cannot approve (403 Forbidden).
   - Frontline agent cannot reject (403 Forbidden).
   - Tier 2 supervisor can approve claims <= ₹25,000.
   - Tier 2 supervisor CANNOT approve High-Value claims > ₹25,000 (403 Forbidden).
   - Senior supervisor CAN approve High-Value claims > ₹25,000.
5. Production authentication boundary:
   - When APP_ENV="production", unauthenticated approval/rejection attempts return 401 Unauthorized.
   - Fallback is strictly disabled in production.
"""

import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.auth import create_access_token, hash_password
from app.database.models import User, Order, SupportCase, ApprovalRequest
from app.database.seed import seed_database


@pytest.fixture(autouse=True)
def ensure_seeded_users(test_db: Session):
    """Ensure database has default test users before each test."""
    seed_database(test_db)


@pytest.fixture
def auth_client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Login Endpoint Tests
# ---------------------------------------------------------------------------

def test_login_successful_supervisor(auth_client):
    """Verify login with valid credentials returns Bearer token and user profile."""
    payload = {
        "username": "supervisor_alice",
        "password": "SupervisorPassword123!",
    }
    resp = auth_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "supervisor_alice"
    assert data["user"]["role"] == "tier2_supervisor"
    assert data["user"]["is_active"] is True


def test_login_successful_senior_supervisor(auth_client):
    """Verify senior supervisor login."""
    payload = {
        "username": "senior_bob",
        "password": "SeniorPassword123!",
    }
    resp = auth_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "senior_supervisor"


def test_login_invalid_password(auth_client):
    """Verify login with incorrect password returns 401 Unauthorized."""
    payload = {
        "username": "supervisor_alice",
        "password": "WrongPassword999!",
    }
    resp = auth_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]


def test_login_unknown_user(auth_client):
    """Verify login with unknown username returns 401 Unauthorized."""
    payload = {
        "username": "unknown_ghost_user",
        "password": "SomePassword123!",
    }
    resp = auth_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]


def test_login_inactive_user(auth_client):
    """Verify inactive user cannot log in (returns 401 Unauthorized)."""
    payload = {
        "username": "inactive_dan",
        "password": "DanPassword123!",
    }
    resp = auth_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 2. Current User Profile Endpoint Tests (/auth/me)
# ---------------------------------------------------------------------------

def test_auth_me_valid_token(auth_client):
    """Verify /auth/me returns user profile with valid Bearer token."""
    login_resp = auth_client.post("/api/v1/auth/login", json={
        "username": "supervisor_alice",
        "password": "SupervisorPassword123!",
    })
    token = login_resp.json()["access_token"]

    resp = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "supervisor_alice"
    assert data["role"] == "tier2_supervisor"


def test_auth_me_missing_token(auth_client):
    """Verify /auth/me without token returns 401 Unauthorized."""
    resp = auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert "Authentication credentials were not provided" in resp.json()["detail"]


def test_auth_me_tampered_token(auth_client):
    """Verify /auth/me with tampered token signature returns 401 Unauthorized."""
    login_resp = auth_client.post("/api/v1/auth/login", json={
        "username": "supervisor_alice",
        "password": "SupervisorPassword123!",
    })
    token = login_resp.json()["access_token"]
    tampered = token[:-6] + "xxxxxx"

    resp = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401
    assert "Could not validate credentials" in resp.json()["detail"]


def test_auth_me_expired_token(auth_client, test_db: Session):
    """Verify /auth/me with expired token returns 401 Unauthorized."""
    expired_token = create_access_token(
        username="supervisor_alice",
        role="tier2_supervisor",
        user_id=1,
        expires_delta_minutes=-10,  # Expired 10 minutes ago
    )

    resp = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "Token has expired" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 3. RBAC Approval and Rejection Boundary Tests
# ---------------------------------------------------------------------------

def _get_token_for(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_rbac_frontline_agent_cannot_approve(auth_client):
    """Verify frontline_agent attempting to approve receives 403 Forbidden."""
    agent_token = _get_token_for(auth_client, "agent_charlie", "AgentPassword123!")

    # Start a case that pauses
    wf_resp = auth_client.post("/api/v1/workflows/resolve", json={
        "complaint_text": "I received my order ORD-2026-001 with damaged packaging and broken armrest and want a replacement.",
        "order_number": "ORD-2026-001",
        "category": "home_appliances",
    })
    assert wf_resp.status_code == 200
    assert wf_resp.json()["status"] == "needs_review"
    tid = wf_resp.json()["thread_id"]

    # Attempt approve with frontline_agent token
    appr_resp = auth_client.post(
        f"/api/v1/workflows/{tid}/approve",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"reviewer_id": "agent_charlie", "reason": "Agent attempting approval"},
    )
    assert appr_resp.status_code == 403
    assert "Frontline agents are not authorized to approve" in appr_resp.json()["detail"]


def test_rbac_frontline_agent_cannot_reject(auth_client):
    """Verify frontline_agent attempting to reject receives 403 Forbidden."""
    agent_token = _get_token_for(auth_client, "agent_charlie", "AgentPassword123!")

    wf_resp = auth_client.post("/api/v1/workflows/resolve", json={
        "complaint_text": "I received my order ORD-2026-001 with damaged packaging and broken armrest and want a replacement.",
        "order_number": "ORD-2026-001",
        "category": "home_appliances",
    })
    assert wf_resp.status_code == 200
    assert wf_resp.json()["status"] == "needs_review"
    tid = wf_resp.json()["thread_id"]

    rej_resp = auth_client.post(
        f"/api/v1/workflows/{tid}/reject",
        headers={"Authorization": f"Bearer {agent_token}"},
        json={"reviewer_id": "agent_charlie", "reason": "Agent attempting rejection"},
    )
    assert rej_resp.status_code == 403
    assert "Frontline agents are not authorized to reject" in rej_resp.json()["detail"]


def test_rbac_tier2_supervisor_can_approve_standard_tier2_case(auth_client):
    """
    ORD-2026-001 has total_amount = ₹19,999.00 (exceeds ₹5k Tier 1, but <= ₹25k High-Value).
    Tier 2 supervisor (supervisor_alice) IS authorized to approve it.
    """
    sup_token = _get_token_for(auth_client, "supervisor_alice", "SupervisorPassword123!")

    wf_resp = auth_client.post("/api/v1/workflows/resolve", json={
        "complaint_text": "I received my order ORD-2026-001 with damaged packaging and broken armrest and want a replacement.",
        "order_number": "ORD-2026-001",
        "category": "home_appliances",
    })
    assert wf_resp.status_code == 200
    assert wf_resp.json()["status"] == "needs_review"
    tid = wf_resp.json()["thread_id"]

    appr_resp = auth_client.post(
        f"/api/v1/workflows/{tid}/approve",
        headers={"Authorization": f"Bearer {sup_token}"},
        json={"reviewer_id": "supervisor_alice", "reason": "Approved by tier 2 supervisor"},
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"
    assert appr_resp.json()["workflow_status"] == "completed"


def test_rbac_tier2_supervisor_cannot_approve_high_value_order(auth_client):
    """
    ORD-2026-003 has total_amount = ₹34,999.00 (EXCEEDS ₹25,000.00 High-Value threshold).
    Tier 2 supervisor (supervisor_alice) must receive 403 Forbidden.
    """
    sup_token = _get_token_for(auth_client, "supervisor_alice", "SupervisorPassword123!")

    # ORD-2026-003 is ₹34,999.00
    wf_resp = auth_client.post("/api/v1/workflows/resolve", json={
        "complaint_text": "High value monitor claim for ORD-2026-003 damaged in transit.",
        "order_number": "ORD-2026-003",
        "category": "electronics",
    })
    tid = wf_resp.json()["thread_id"]

    appr_resp = auth_client.post(
        f"/api/v1/workflows/{tid}/approve",
        headers={"Authorization": f"Bearer {sup_token}"},
        json={"reviewer_id": "supervisor_alice", "reason": "Tier 2 attempting high-value approval"},
    )
    assert appr_resp.status_code == 403
    assert "High-value claim" in appr_resp.json()["detail"]
    assert "requires senior_supervisor co-authorization" in appr_resp.json()["detail"]


def test_rbac_senior_supervisor_can_approve_high_value_order(auth_client):
    """
    Senior supervisor (senior_bob) IS authorized to approve High-Value claims > ₹25,000.
    """
    senior_token = _get_token_for(auth_client, "senior_bob", "SeniorPassword123!")

    # ORD-2026-003 is ₹34,999.00
    wf_resp = auth_client.post("/api/v1/workflows/resolve", json={
        "complaint_text": "High value monitor claim for ORD-2026-003 damaged in transit.",
        "order_number": "ORD-2026-003",
        "category": "electronics",
    })
    tid = wf_resp.json()["thread_id"]

    appr_resp = auth_client.post(
        f"/api/v1/workflows/{tid}/approve",
        headers={"Authorization": f"Bearer {senior_token}"},
        json={"reviewer_id": "senior_bob", "reason": "Senior supervisor co-authorized per policy"},
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"
    assert appr_resp.json()["workflow_status"] == "completed"


# ---------------------------------------------------------------------------
# 4. Production Mode Boundary Enforcement Tests
# ---------------------------------------------------------------------------

def test_production_mode_rejects_unauthenticated_approval(auth_client, monkeypatch):
    """
    When APP_ENV='production', unauthenticated requests without Bearer token
    MUST receive 401 Unauthorized. Fallback is strictly disabled.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")

    wf_resp = auth_client.post("/api/v1/workflows/resolve", json={
        "complaint_text": "I received my order ORD-2026-001 with damaged packaging and broken armrest and want a replacement.",
        "order_number": "ORD-2026-001",
        "category": "home_appliances",
    })
    assert wf_resp.status_code == 200
    assert wf_resp.json()["status"] == "needs_review"
    tid = wf_resp.json()["thread_id"]

    # Call /approve without Authorization header
    appr_resp = auth_client.post(
        f"/api/v1/workflows/{tid}/approve",
        json={"reviewer_id": "anonymous_caller", "reason": "Trying unauthenticated approval"},
    )
    assert appr_resp.status_code == 401
    assert "Authentication required" in appr_resp.json()["detail"]
    assert "strictly prohibited in production" in appr_resp.json()["detail"]


def test_production_mode_rejects_unauthenticated_rejection(auth_client, monkeypatch):
    """
    When APP_ENV='production', unauthenticated rejection attempts receive 401 Unauthorized.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")

    wf_resp = auth_client.post("/api/v1/workflows/resolve", json={
        "complaint_text": "I received my order ORD-2026-001 with damaged packaging and broken armrest and want a replacement.",
        "order_number": "ORD-2026-001",
        "category": "home_appliances",
    })
    assert wf_resp.status_code == 200
    assert wf_resp.json()["status"] == "needs_review"
    tid = wf_resp.json()["thread_id"]

    rej_resp = auth_client.post(
        f"/api/v1/workflows/{tid}/reject",
        json={"reviewer_id": "anonymous_caller", "reason": "Trying unauthenticated rejection"},
    )
    assert rej_resp.status_code == 401
    assert "Authentication required" in rej_resp.json()["detail"]
