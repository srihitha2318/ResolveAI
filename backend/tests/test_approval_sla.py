"""
Test Suite for Level 6 Phase 2: Approval SLA Management.
Verifies configurable SLA deadlines, priority assignment, idempotent overdue evaluation,
audit logging, UTC handling, and server-side protection preventing unauthorized or ordinary
processing of expired approval requests.
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Generator
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.auth import (
    ROLE_FRONTLINE_AGENT,
    ROLE_SENIOR_SUPERVISOR,
    ROLE_TIER2_SUPERVISOR,
    create_access_token,
)
from app.core.config import settings
from app.core.policy_rules import HIGH_VALUE_THRESHOLD_PAISE
from app.core.sla import (
    SLA_PRIORITY_HIGH,
    SLA_PRIORITY_STANDARD,
    calculate_sla_parameters,
    ensure_utc,
    evaluate_and_record_sla_breach,
    evaluate_pending_approvals_slas,
    get_time_remaining_seconds,
    is_approval_expired,
    validate_approval_decision_sla,
)
from app.database.db import get_db, SessionLocal
from app.database.init_db import migrate_approval_requests_schema
from app.database.models import ApprovalRequest, CaseEvent, Customer, Order, SupportCase, utc_now
from app.tools.support_tools import (
    create_or_update_approval_request,
    get_approval_request_by_thread_id,
    get_pending_approval_requests,
)
from app.database.seed import seed_database
from main import app


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers_senior(db_session: Session) -> dict:
    token = create_access_token(username="senior_bob", role=ROLE_SENIOR_SUPERVISOR, user_id=2)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_tier2(db_session: Session) -> dict:
    token = create_access_token(username="supervisor_alice", role=ROLE_TIER2_SUPERVISOR, user_id=1)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_agent(db_session: Session) -> dict:
    token = create_access_token(username="agent_charlie", role=ROLE_FRONTLINE_AGENT, user_id=3)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def isolated_case_and_order(db_session: Session):
    """Creates a temporary customer, order, and support case for SLA testing."""
    uid = uuid.uuid4().hex[:8]
    cust = Customer(name=f"SLA Test Customer {uid}", email=f"sla_{uid}@test.com")
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)

    order = Order(
        order_number=f"ORD-SLA-{uid}",
        customer_id=cust.id,
        product_name="Test SLA Product",
        order_status="delivered",
        delivery_status="delivered",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
        expected_delivery_date=datetime.now(timezone.utc) - timedelta(days=1),
        delivered_at=datetime.now(timezone.utc) - timedelta(days=1),
        total_amount=150000,  # ₹1,500.00 (Standard Tier 2)
        currency="INR",
        category="electronics",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    case = SupportCase(
        case_number=f"CASE-SLA-{uid}",
        customer_id=cust.id,
        order_id=order.id,
        subject="SLA Test Case",
        complaint_text="SLA evaluation complaint",
        status="escalated",
        priority="medium",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    return {"customer": cust, "order": order, "case": case}


# ---------------------------------------------------------------------------
# 1. SLA Assignment and Expiration Timestamps
# ---------------------------------------------------------------------------

def test_sla_assignment_standard_order():
    """Standard order (<= ₹25,000) assigns standard priority, tier2 role, and standard hours."""
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    params = calculate_sla_parameters(order_amount_paise=150000, created_at=now)

    assert params["sla_priority"] == SLA_PRIORITY_STANDARD
    assert params["required_role"] == ROLE_TIER2_SUPERVISOR
    assert params["sla_hours"] == settings.SLA_STANDARD_HOURS
    assert params["expires_at"] == now + timedelta(hours=settings.SLA_STANDARD_HOURS)
    assert not params["is_high_value"]


def test_sla_assignment_high_value_order():
    """High-value order (> ₹25,000) assigns high priority, senior role, and high-value hours."""
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    # ₹35,000.00 (3,500,000 paise)
    params = calculate_sla_parameters(order_amount_paise=3500000, created_at=now)

    assert params["sla_priority"] == SLA_PRIORITY_HIGH
    assert params["required_role"] == ROLE_SENIOR_SUPERVISOR
    assert params["sla_hours"] == settings.SLA_HIGH_VALUE_HOURS
    assert params["expires_at"] == now + timedelta(hours=settings.SLA_HIGH_VALUE_HOURS)
    assert params["is_high_value"]


def test_sla_durations_configurable(monkeypatch):
    """SLA durations respect configured settings overrides without hardcoding."""
    monkeypatch.setattr(settings, "SLA_STANDARD_HOURS", 24)
    monkeypatch.setattr(settings, "SLA_HIGH_VALUE_HOURS", 2)

    now = datetime.now(timezone.utc)
    std_params = calculate_sla_parameters(order_amount_paise=100000, created_at=now)
    assert std_params["sla_hours"] == 24
    assert std_params["expires_at"] == now + timedelta(hours=24)

    high_params = calculate_sla_parameters(order_amount_paise=HIGH_VALUE_THRESHOLD_PAISE + 100, created_at=now)
    assert high_params["sla_hours"] == 2
    assert high_params["expires_at"] == now + timedelta(hours=2)


# ---------------------------------------------------------------------------
# 2. Expiration Evaluation, Overdue Status, and UTC Handling
# ---------------------------------------------------------------------------

def test_pending_request_not_expired(db_session: Session, isolated_case_and_order: dict):
    """Pending request with future expiration timestamp is not marked expired."""
    case = isolated_case_and_order["case"]
    thread_id = f"test-sla-thread-{uuid.uuid4().hex[:6]}"

    created = create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="refund",
        justification="Pending unexpired test",
    )

    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == created["id"])
    ).scalar_one()

    assert not approval.is_expired
    assert not is_approval_expired(approval)
    assert get_time_remaining_seconds(approval) > 0


def test_expired_request_evaluation_and_audit_event(db_session: Session, isolated_case_and_order: dict):
    """Overdue request is marked is_expired=True and an auditable case event is recorded."""
    case = isolated_case_and_order["case"]
    thread_id = f"test-sla-expired-{uuid.uuid4().hex[:6]}"

    created = create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="replacement",
        justification="Expired test",
    )

    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == created["id"])
    ).scalar_one()

    # Simulate past deadline (expired 2 hours ago)
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    approval.expires_at = past_time
    db_session.commit()

    # Evaluate SLA
    was_marked = evaluate_and_record_sla_breach(db_session, approval)
    db_session.commit()
    db_session.refresh(approval)

    assert was_marked is True
    assert approval.is_expired is True
    assert approval.status == "pending"  # Crucial: status does NOT silently change!

    # Check case event
    evt = db_session.execute(
        select(CaseEvent).where(
            CaseEvent.case_id == case.id,
            CaseEvent.event_type == "sla_breached",
        )
    ).scalar_one_or_none()

    assert evt is not None
    assert "breached target SLA deadline" in evt.message
    details = json.loads(evt.details_json)
    assert details["approval_id"] == approval.id
    assert details["sla_priority"] == approval.sla_priority


def test_repeated_sla_checks_no_duplicate_events(db_session: Session, isolated_case_and_order: dict):
    """Repeated evaluations of the same overdue request do not duplicate case events."""
    case = isolated_case_and_order["case"]
    thread_id = f"test-sla-dup-{uuid.uuid4().hex[:6]}"

    created = create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="refund",
        justification="Duplicate event check",
    )

    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == created["id"])
    ).scalar_one()
    approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    # Run check 3 times
    res1 = evaluate_and_record_sla_breach(db_session, approval)
    db_session.commit()
    res2 = evaluate_and_record_sla_breach(db_session, approval)
    db_session.commit()
    res3 = evaluate_and_record_sla_breach(db_session, approval)
    db_session.commit()

    assert res1 is True
    assert res2 is False
    assert res3 is False

    events = db_session.scalars(
        select(CaseEvent).where(
            CaseEvent.case_id == case.id,
            CaseEvent.event_type == "sla_breached",
        )
    ).all()
    assert len(events) == 1


def test_utc_timestamp_handling():
    """Consistent UTC normalization handles naive and timezone-aware datetimes."""
    naive_dt = datetime(2026, 10, 10, 14, 0, 0)
    aware_dt = datetime(2026, 10, 10, 14, 0, 0, tzinfo=timezone.utc)

    norm_naive = ensure_utc(naive_dt)
    norm_aware = ensure_utc(aware_dt)

    assert norm_naive.tzinfo == timezone.utc
    assert norm_aware.tzinfo == timezone.utc
    assert norm_naive == norm_aware


# ---------------------------------------------------------------------------
# 3. Server-Side Protection Against Processing Expired Approvals
# ---------------------------------------------------------------------------

def test_tier2_supervisor_cannot_approve_expired_request(
    test_client: TestClient,
    db_session: Session,
    auth_headers_tier2: dict,
    isolated_case_and_order: dict,
):
    """Tier 2 supervisor cannot approve an expired request through ordinary flow (403 Forbidden)."""
    case = isolated_case_and_order["case"]
    thread_id = f"thread-exp-tier2-{uuid.uuid4().hex[:6]}"

    created = create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="refund",
        justification="Tier2 expired test",
    )
    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == created["id"])
    ).scalar_one()
    approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    approval.is_expired = True
    db_session.commit()

    resp = test_client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=auth_headers_tier2,
        json={"reviewer_id": "supervisor_alice", "reason": "Attempting tier2 approve on expired"},
    )

    assert resp.status_code == 403
    assert "breached its SLA deadline" in resp.json()["detail"]
    assert "senior supervisor authorization" in resp.json()["detail"].lower()


def test_frontline_agent_cannot_approve_expired_request(
    test_client: TestClient,
    db_session: Session,
    auth_headers_agent: dict,
    isolated_case_and_order: dict,
):
    """Frontline agent cannot approve an expired request (403 Forbidden)."""
    case = isolated_case_and_order["case"]
    thread_id = f"thread-exp-agent-{uuid.uuid4().hex[:6]}"

    created = create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="refund",
        justification="Agent expired test",
    )
    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == created["id"])
    ).scalar_one()
    approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    approval.is_expired = True
    db_session.commit()

    resp = test_client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=auth_headers_agent,
        json={"reviewer_id": "agent_charlie", "reason": "Agent approving expired"},
    )

    assert resp.status_code == 403


def test_senior_supervisor_cannot_approve_expired_without_explicit_override(
    test_client: TestClient,
    db_session: Session,
    auth_headers_senior: dict,
    isolated_case_and_order: dict,
):
    """Senior supervisor cannot approve an expired request without explicit override_expired=True (400 Bad Request)."""
    case = isolated_case_and_order["case"]
    thread_id = f"thread-exp-senior-no-override-{uuid.uuid4().hex[:6]}"

    created = create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="refund",
        justification="Senior without override",
    )
    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == created["id"])
    ).scalar_one()
    approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    approval.is_expired = True
    db_session.commit()

    resp = test_client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        headers=auth_headers_senior,
        json={
            "reviewer_id": "senior_bob",
            "reason": "Senior approving without override flag",
            "override_expired": False,
        },
    )

    assert resp.status_code == 400
    assert "override_expired" in resp.json()["detail"].lower()


def test_senior_supervisor_can_approve_expired_with_explicit_override(
    test_client: TestClient,
    db_session: Session,
    auth_headers_senior: dict,
    isolated_case_and_order: dict,
):
    """Senior supervisor can approve an expired request by explicitly specifying override_expired=True."""
    case = isolated_case_and_order["case"]
    # Initialize a LangGraph paused checkpoint thread
    thread_id = f"thread-exp-override-success-{uuid.uuid4().hex[:6]}"

    # Start a real workflow that escalates
    res_init = test_client.post(
        "/api/v1/workflows/resolve",
        json={
            "order_number": "ORD-2026-001",
            "complaint_text": "I received my order ORD-2026-001 with damaged packaging and broken armrest and want a replacement.",
            "category": "home_appliances",
            "thread_id": thread_id,
        },
    )
    assert res_init.status_code == 200
    assert res_init.json()["status"] == "needs_review"
    tid = res_init.json()["thread_id"]

    # Mark approval as expired in db_session
    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.thread_id == tid)
    ).scalar_one()
    approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=3)
    approval.is_expired = True
    case_id = approval.case_id
    db_session.commit()

    # Now approve with explicit override_expired=True
    resp = test_client.post(
        f"/api/v1/workflows/{tid}/approve",
        headers=auth_headers_senior,
        json={
            "reviewer_id": "senior_bob",
            "reason": "Senior supervisor approved overdue exception per customer lifetime value.",
            "override_expired": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["is_expired_override"] is True

    # Verify audit event recorded
    override_evt = db_session.execute(
        select(CaseEvent).where(
            CaseEvent.case_id == case_id,
            CaseEvent.event_type == "expired_approval_override",
        )
    ).scalar_one_or_none()

    assert override_evt is not None
    assert "authorized approval override" in override_evt.message


def test_expiration_does_not_silently_approve_or_reject(
    db_session: Session,
    isolated_case_and_order: dict,
):
    """SLA expiration marks is_expired but NEVER silently completes, approves, or rejects."""
    case = isolated_case_and_order["case"]
    thread_id = f"thread-silent-guard-{uuid.uuid4().hex[:6]}"

    created = create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="refund",
        justification="Silence guard test",
    )
    approval = db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == created["id"])
    ).scalar_one()
    approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=5)
    db_session.commit()

    evaluate_pending_approvals_slas(db_session)
    db_session.refresh(approval)

    assert approval.is_expired is True
    assert approval.status == "pending"
    assert approval.workflow_status == "pending_review"
    assert approval.decision_reason is None
    assert approval.decision_timestamp is None


# ---------------------------------------------------------------------------
# 4. Additive Migration and API Metadata Exposure
# ---------------------------------------------------------------------------

def test_idempotent_additive_migration(db_session: Session):
    """Running additive migration multiple times causes no errors and preserves all columns."""
    engine = db_session.get_bind()
    migrate_approval_requests_schema(engine)
    migrate_approval_requests_schema(engine)

    result = db_session.execute(text("PRAGMA table_info(approval_requests)"))
    columns = {row[1] for row in result.fetchall()}

    assert "expires_at" in columns
    assert "sla_priority" in columns
    assert "required_role" in columns
    assert "is_expired" in columns


def test_pending_approvals_api_exposes_sla_metadata(
    test_client: TestClient,
    db_session: Session,
    isolated_case_and_order: dict,
):
    """GET pending approvals endpoints expose SLA deadline, priority, role, and expiration status."""
    case = isolated_case_and_order["case"]
    thread_id = f"thread-api-sla-{uuid.uuid4().hex[:6]}"

    create_or_update_approval_request(
        db=db_session,
        case_id=case.id,
        thread_id=thread_id,
        requested_action="replacement",
        justification="API exposure test",
    )

    # 1. List pending
    list_resp = test_client.get("/api/v1/workflows/pending-approvals")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    target_item = next((i for i in items if i["thread_id"] == thread_id), None)
    assert target_item is not None
    assert target_item["sla_priority"] in (SLA_PRIORITY_STANDARD, SLA_PRIORITY_HIGH)
    assert target_item["required_role"] in (ROLE_TIER2_SUPERVISOR, ROLE_SENIOR_SUPERVISOR)
    assert target_item["expires_at"] is not None
    assert isinstance(target_item["is_expired"], bool)

    # 2. Detail
    detail_resp = test_client.get(f"/api/v1/workflows/{thread_id}/approval")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["expires_at"] is not None
    assert detail["sla_priority"] == target_item["sla_priority"]
    assert detail["required_role"] == target_item["required_role"]
    assert detail["is_expired"] == target_item["is_expired"]
