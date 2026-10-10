"""
Tests for ResolveAI Level 6 Phase 4: Dashboard Enhancements.
Covers:
1. Dashboard HTML serving, SEO structure, and presence of all Phase 4 elements.
2. Authentication flow: Login, profile retrieval, invalid credentials, and token expiration.
3. Pending Clarifications API: list and detail endpoints.
4. Role-Based Authorization: Frontline agent restriction, Tier 2 threshold guard, Senior Supervisor authority.
5. SLA Monitoring metadata and expiration handling.
6. Expired approval override confirmation.
7. Staff clarification submission and workflow resumption on behalf of customer.
"""

from datetime import datetime, timezone, timedelta
import json
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.main import app
from app.database.db import SessionLocal
from app.core.auth import create_access_token
from app.database.models import User, Customer, Order, SupportCase, ApprovalRequest, CaseEvent, utc_now


@pytest.fixture
def client():
    """Isolated FastAPI test client for dashboard routes."""
    return TestClient(app)


@pytest.fixture
def frontline_headers(client):
    """Bearer headers for frontline agent charlie."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "agent_charlie", "password": "AgentPassword123!"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tier2_headers(client):
    """Bearer headers for tier 2 supervisor alice."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "supervisor_alice", "password": "SupervisorPassword123!"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def senior_headers(client):
    """Bearer headers for senior supervisor bob."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "senior_bob", "password": "SeniorPassword123!"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Dashboard HTML Interface Verification
# ---------------------------------------------------------------------------

def test_dashboard_html_contains_all_phase4_elements(client: TestClient):
    """
    Verify GET /dashboard serves the enhanced HTML command center with all
    required Phase 4 interactive components, headers, modals, and elements.
    """
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text

    # Brand and SEO requirements
    assert "ResolveAI" in html
    assert "Supervisor Command" in html
    assert "Clarification Center" in html
    assert "<h1" in html

    # Authentication interface elements
    assert "loginModal" in html
    assert "loginUsername" in html
    assert "loginPassword" in html
    assert "btnLoginSubmit" in html
    assert "authActionBtn" in html
    assert "userProfileChip" in html
    assert "userRoleBadge" in html
    assert "sessionStorage" in html  # Verifies secure tab-scoped browser storage

    # Queue navigation tabs
    assert "tabApprovalsBtn" in html
    assert "tabClarificationsBtn" in html
    assert "queueListApprovals" in html
    assert "queueListClarifications" in html

    # SLA metrics and indicators
    assert "metricPendingApprovals" in html
    assert "metricPendingClarifications" in html
    assert "metricSlaOverdue" in html
    assert "metricRoleAuthority" in html

    # Approval and rejection action controls
    assert "btnApprove" in html
    assert "btnReject" in html
    assert "approveModal" in html
    assert "rejectModal" in html
    assert "approvalNotesInput" in html
    assert "rejectionReasonInput" in html
    assert "approveOverrideExpiredCheckbox" in html

    # Customer clarification intake form
    assert "clarifyOrderNumber" in html
    assert "clarifyDetails" in html
    assert "clarifyCategory" in html
    assert "btnSubmitClarification" in html


# ---------------------------------------------------------------------------
# 2. Authentication and Session Validation
# ---------------------------------------------------------------------------

def test_dashboard_auth_login_successful(client: TestClient):
    """Verify login API authenticates staff and provides JWT token for dashboard."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "supervisor_alice", "password": "SupervisorPassword123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "tier2_supervisor"
    assert data["user"]["username"] == "supervisor_alice"

    # Validate auth/me endpoint
    token = data["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "supervisor_alice"
    assert me_data["role"] == "tier2_supervisor"


def test_dashboard_auth_invalid_credentials(client: TestClient):
    """Verify invalid password returns 401 Unauthorized."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "supervisor_alice", "password": "WrongPassword999!"},
    )
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]


def test_dashboard_auth_token_expiration_and_tampering(client: TestClient):
    """Verify tampered or expired tokens return 401 to prompt re-login."""
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token.value"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. Pending Clarifications API
# ---------------------------------------------------------------------------

def test_pending_clarifications_list_endpoint(client: TestClient):
    """Verify GET /api/v1/workflows/pending-clarifications returns paginated queue."""
    resp = client.get("/api/v1/workflows/pending-clarifications?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_count" in data
    assert "items" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)


def test_clarification_detail_endpoint_not_found(client: TestClient):
    """Verify querying non-existent thread for clarification returns 404."""
    resp = client.get("/api/v1/workflows/non-existent-thread-12345/clarification")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_clarification_detail_endpoint_for_waiting_thread(client: TestClient):
    """Verify GET /api/v1/workflows/{thread_id}/clarification returns detailed context."""
    # Run a workflow with missing order to generate a paused clarification thread
    res = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "I bought an expensive camera but have no order number.",
            "order_number": "ORD-MISSING-DASH-TEST",
        },
    )
    assert res.status_code == 200
    init_data = res.json()
    thread_id = init_data["thread_id"]
    assert init_data["status"] == "needs_information"

    # Inspect clarification detail endpoint
    det_resp = client.get(f"/api/v1/workflows/{thread_id}/clarification")
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    assert det_data["thread_id"] == thread_id
    assert det_data["status"] == "needs_information"
    assert len(det_data["missing_information"]) > 0
    assert det_data["clarification_details"] is not None


# ---------------------------------------------------------------------------
# 4. Role-Based Authorization Enforcement
# ---------------------------------------------------------------------------

def test_role_based_controls_frontline_agent_restricted(client: TestClient, frontline_headers):
    """
    Verify frontline agent cannot approve or reject pending supervisor approvals.
    Backend must enforce 403 Forbidden.
    """
    # Create high-value case requiring supervisor review
    wf_res = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "My ₹18,999 electronics item arrived completely shattered.",
            "order_number": "ORD-2026-003",
        },
    )
    assert wf_res.status_code == 200
    thread_id = wf_res.json()["thread_id"]

    # Frontline agent attempts approval -> 403
    app_resp = client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=frontline_headers,
        json={"reviewer_id": "agent_charlie", "reason": "Attempted approval"},
    )
    assert app_resp.status_code == 403
    assert "not authorized" in app_resp.json()["detail"].lower()

    # Frontline agent attempts rejection -> 403
    rej_resp = client.post(
        f"/api/v1/workflows/{thread_id}/reject",
        headers=frontline_headers,
        json={"reviewer_id": "agent_charlie", "reason": "Attempted rejection"},
    )
    assert rej_resp.status_code == 403
    assert "not authorized" in rej_resp.json()["detail"].lower()


def test_role_based_controls_tier2_threshold_enforcement(client: TestClient, tier2_headers, senior_headers):
    """
    Verify Tier 2 Supervisor is barred from approving high-value cases > ₹25,000 (403),
    while Senior Supervisor is authorized.
    """
    wf_res = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "My ₹34,999 electronics item arrived damaged.",
            "order_number": "ORD-2026-003",
        },
    )
    assert wf_res.status_code == 200
    thread_id = wf_res.json()["thread_id"]

    # Tier 2 supervisor attempts approval of ₹34,999 case -> 403
    t2_resp = client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=tier2_headers,
        json={"reviewer_id": "supervisor_alice", "reason": "Approving"},
    )
    assert t2_resp.status_code == 403
    assert "requires senior_supervisor" in t2_resp.json()["detail"].lower()
    assert "25,000" in t2_resp.json()["detail"]

    # Senior supervisor approves successfully
    senior_resp = client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=senior_headers,
        json={"reviewer_id": "senior_bob", "reason": "Senior supervisor authorization verified."},
    )
    assert senior_resp.status_code == 200
    assert senior_resp.json()["status"] == "approved"


# ---------------------------------------------------------------------------
# 5. SLA Expiration Display and Override Confirmation
# ---------------------------------------------------------------------------

def test_expired_approval_override_interaction(client: TestClient, tier2_headers, senior_headers):
    """
    Verify expired approval requests require explicit senior supervisor override
    (override_expired=True) and reject unauthorized Tier 2 or missing override attempts.
    """
    # Create an approval case within Tier 2 limit (ORD-2026-001 is ₹8,999 <= ₹25,000)
    wf_res = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "I received my smartphone ORD-2026-001 with a cracked screen and want a full refund.",
            "order_number": "ORD-2026-001",
            "category": "electronics",
        },
    )
    thread_id = wf_res.json()["thread_id"]

    # Manually expire the approval request in DB using SessionLocal
    with SessionLocal() as db:
        app_obj = db.execute(
            select(ApprovalRequest).where(ApprovalRequest.thread_id == thread_id)
        ).scalar_one()
        past_time = utc_now() - timedelta(hours=2)
        app_obj.expires_at = past_time
        app_obj.is_expired = True
        db.commit()

    # 1. Tier 2 attempts approval on expired request -> 403 (blocked specifically by expired SLA)
    t2_resp = client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=tier2_headers,
        json={"reviewer_id": "supervisor_alice", "reason": "Tier 2 attempt"},
    )
    assert t2_resp.status_code == 403
    assert "expired" in t2_resp.json()["detail"].lower()

    # 2. Senior supervisor attempts approval without override confirmation -> 400
    senior_no_override = client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=senior_headers,
        json={"reviewer_id": "senior_bob", "reason": "Approving without checkbox", "override_expired": False},
    )
    assert senior_no_override.status_code == 400
    assert "override" in senior_no_override.json()["detail"].lower()

    # 3. Senior supervisor approves with explicit override confirmation -> 200 OK
    senior_with_override = client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=senior_headers,
        json={
            "reviewer_id": "senior_bob",
            "reason": "Authorized expired approval override per Senior review",
            "override_expired": True,
        },
    )
    assert senior_with_override.status_code == 200
    assert senior_with_override.json()["status"] == "approved"
    assert senior_with_override.json()["is_expired_override"] is True


# ---------------------------------------------------------------------------
# 6. Staff Clarification Submission via Dashboard
# ---------------------------------------------------------------------------

def test_staff_submits_clarification_on_behalf_of_customer(client: TestClient, frontline_headers):
    """
    Verify authenticated staff member (e.g. Frontline Agent) can submit customer-provided
    clarification through the dashboard, resuming the paused workflow.
    """
    # Create thread awaiting customer info with specific defect description
    init_res = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "My USB-C docking station arrived with a damaged port, but order number was omitted.",
            "order_number": "ORD-NOT-FOUND-DASH-1",
            "category": "electronics",
            "customer_id": 3,
        },
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    thread_id = init_data["thread_id"]
    assert init_data["status"] == "needs_information"

    # Frontline agent submits valid clarification received from customer
    clarify_resp = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        headers=frontline_headers,
        json={
            "order_number": "ORD-2026-005",  # Valid electronics order for customer 3
            "additional_details": "Customer confirmed order number ORD-2026-005 with unboxing photo showing damaged port.",
            "category": "electronics",
        },
    )
    assert clarify_resp.status_code == 200
    res_data = clarify_resp.json()
    assert res_data["thread_id"] == thread_id
    assert res_data["status"] in ("completed", "needs_review", "resumed")
    assert res_data["workflow_status"] == "completed"
