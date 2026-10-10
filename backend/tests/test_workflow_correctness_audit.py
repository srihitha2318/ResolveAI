"""
Focused Level 4 correctness audit regression tests.
Audits and verifies:
1. When requires_supervisor_approval is True, the final response cannot report
   status='completed' and needs_review=False before human approval.
2. The order of conditional routing ensures approval-required cases, policy conflicts,
   and insufficient evidence cannot be bypassed by successful verification.
3. Missing orders and missing information route correctly to needs_information.
4. Failed verification cannot result in a completed resolution.
5. Case events accurately reflect final status (completed, needs_review, needs_information, failed).
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workflows import (
    initialize_workflow_state,
    run_resolution_workflow,
)
from app.workflows.routing import route_after_verification
from app.workflows.nodes import record_resolution_node, finalize_response_node
from app.schemas.agent_schemas import (
    ComplaintAnalysisResult,
    OrderInvestigationResult,
    PolicyRetrievalResult,
    ResolutionRecommendationResult,
    VerificationResult,
)


@pytest.fixture
def api_client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Audit Issue 1: Supervisor Approval Safety
# ---------------------------------------------------------------------------

def test_requires_supervisor_approval_cannot_report_completed():
    """
    Verify that if requires_supervisor_approval (or human_approval_required) is True,
    the workflow cannot report status='completed' and needs_review=False.
    """
    state = initialize_workflow_state(
        complaint_text="My laptop screen is cracked.",
        order_number="ORD-2026-001",
    )
    state["requires_supervisor_approval"] = True
    state["recommended_resolution"] = {
        "recommendation_type": "escalate_to_human",
        "title": "High-Value Damage Claim",
        "reasoning": "Exceeds threshold",
        "action_required": "Supervisor review required",
        "human_approval_required": True,
        "requires_supervisor_approval": True,
        "method": "rule_based",
    }
    state["verification_result"] = {
        "verification_status": "pass",
        "is_valid": True,
        "detected_issues": [],
        "evidence_checked": ["order_exists"],
        "missing_evidence": [],
        "required_next_step": "supervisor_approval",
    }

    # Router must divert to escalate_case
    destination = route_after_verification(state)
    assert destination == "escalate_case"

    # Even if finalize_response_node were called on a state with requires_supervisor_approval
    state["workflow_status"] = "completed"
    state["needs_review"] = False
    finalized = finalize_response_node(state)
    assert finalized["workflow_status"] != "completed"
    assert finalized["workflow_status"] == "needs_review"
    assert finalized["needs_review"] is True


def test_api_supervisor_approval_reports_needs_review(api_client):
    """
    Verify that an API request on a high-value order (> ₹5,000.00 like ORD-2026-001)
    returns status='needs_review' and needs_review=True, never 'completed'.
    """
    payload = {
        "complaint_text": "The laptop delivered in order ORD-2026-001 has a shattered display.",
        "order_number": "ORD-2026-001",
        "category": "electronics",
    }
    response = api_client.post("/api/v1/workflows/resolve", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "needs_review"
    assert data["needs_review"] is True
    assert data["status"] != "completed"
    assert data["escalation_reason"] is not None


# ---------------------------------------------------------------------------
# Audit Issue 2: Routing Order & Priority (Conflict & Insufficient Evidence)
# ---------------------------------------------------------------------------

def test_routing_order_policy_conflict_never_bypassed_by_valid_verification():
    """
    Verify that a policy conflict (needs_review) escalates even if verification
    evaluates is_valid as True.
    """
    state = initialize_workflow_state(
        complaint_text="Complaint with conflict",
        order_number="ORD-2026-001",
    )
    state["policy_conflict_status"] = "needs_review"
    state["verification_result"] = {
        "verification_status": "pass",
        "is_valid": True,
        "detected_issues": [],
    }

    decision = route_after_verification(state)
    assert decision == "escalate_case"


def test_routing_order_insufficient_evidence_escalates_for_any_category():
    """
    Verify that insufficient policy evidence triggers escalation across ANY category,
    not just hardcoded categories.
    """
    for cat in ["electronics", "general_merchandise", "other", "unknown_category"]:
        state = initialize_workflow_state(
            complaint_text=f"Complaint in {cat}",
            order_number="ORD-2026-001",
            category=cat,
        )
        state["insufficient_evidence"] = True
        state["complaint_category"] = cat
        state["verification_result"] = {
            "verification_status": "pass",
            "is_valid": True,
        }

        decision = route_after_verification(state)
        assert decision == "escalate_case", f"Failed to escalate for category '{cat}'"


# ---------------------------------------------------------------------------
# Audit Issue 3: Missing Orders and Information
# ---------------------------------------------------------------------------

def test_missing_order_routes_to_needs_information():
    """
    Verify that when an order does not exist, the workflow routes to
    handle_missing_information with status='needs_information'.
    """
    res = run_resolution_workflow(
        complaint_text="Where is my order ORD-NONEXISTENT-999?",
        order_number="ORD-NONEXISTENT-999",
    )
    assert res["workflow_status"] == "needs_information"
    assert res["missing_order"] is True
    assert res["order_investigation"]["order_exists"] is False
    assert len(res["missing_information"]) > 0


def test_missing_order_not_bypassed_even_if_verification_is_valid():
    """
    Verify that if order does not exist, it routes to handle_missing_information
    even if a verification result object exists and reports valid.
    """
    state = initialize_workflow_state(
        complaint_text="Nonexistent order check",
        order_number="ORD-000",
    )
    state["missing_order"] = True
    state["order_investigation"] = {"order_exists": False}
    state["verification_result"] = {"is_valid": True, "verification_status": "pass"}

    decision = route_after_verification(state)
    assert decision == "handle_missing_information"


# ---------------------------------------------------------------------------
# Audit Issue 4: Failed Verification Cannot Complete Resolution
# ---------------------------------------------------------------------------

def test_failed_verification_cannot_result_in_completed_resolution():
    """
    Verify that a failed verification (e.g. false completion claims or contradiction)
    triggers bounded recovery or escalation, and never reports status='completed'.
    """
    # 1. First failure triggers recovery (retry_count 0 < max_retries 1)
    state = initialize_workflow_state(
        complaint_text="Product complaint",
        order_number="ORD-2026-001",
        max_retries=1,
    )
    state["retry_count"] = 0
    state["verification_result"] = {
        "verification_status": "fail",
        "is_valid": False,
        "detected_issues": ["Contradicts stored delivery status"],
    }

    decision_1 = route_after_verification(state)
    assert decision_1 == "attempt_recovery"

    # 2. Second failure triggers escalation (retry_count 1 >= max_retries 1)
    state["retry_count"] = 1
    decision_2 = route_after_verification(state)
    assert decision_2 == "escalate_case"


def test_record_resolution_safety_invariant_guard():
    """
    Verify that record_resolution_node defensively refuses to complete a case
    if approval is required, conflict exists, evidence is insufficient, or verification failed.
    """
    state = initialize_workflow_state(complaint_text="Direct node call test")

    # A: Requires supervisor approval -> diverted to escalate_case
    state["requires_supervisor_approval"] = True
    res_a = record_resolution_node(state)
    assert res_a["workflow_status"] == "needs_review"
    assert res_a["current_stage"] == "escalate_case"

    # B: Policy conflict -> diverted to escalate_case
    state["requires_supervisor_approval"] = False
    state["policy_conflict_status"] = "needs_review"
    res_b = record_resolution_node(state)
    assert res_b["workflow_status"] == "needs_review"

    # C: Missing order -> diverted to handle_missing_information
    state["policy_conflict_status"] = "resolved"
    state["missing_order"] = True
    res_c = record_resolution_node(state)
    assert res_c["workflow_status"] == "needs_information"

    # D: Verification failed -> diverted to escalate_case
    state["missing_order"] = False
    state["verification_result"] = {"is_valid": False, "verification_status": "fail"}
    res_d = record_resolution_node(state)
    assert res_d["workflow_status"] == "needs_review"


# ---------------------------------------------------------------------------
# Audit Issue 5: Case Events Accurately Reflect Final Status
# ---------------------------------------------------------------------------

def test_case_events_reflect_final_status():
    """
    Verify that persisted events match final workflow status:
    - needs_information has case_needs_information
    - needs_review has case_needs_review
    """
    # Test needs_information
    res_info = run_resolution_workflow(
        complaint_text="Missing order ORD-99999",
        order_number="ORD-99999",
    )
    assert res_info["workflow_status"] == "needs_information"
    event_types_info = [e["event_type"] for e in res_info["events_recorded"]]
    assert "case_needs_information" in event_types_info

    # Test needs_review
    res_review = run_resolution_workflow(
        complaint_text="The expensive laptop in ORD-2026-001 has broken screen.",
        order_number="ORD-2026-001",
        category="electronics",
    )
    assert res_review["workflow_status"] == "needs_review"
    event_types_review = [e["event_type"] for e in res_review["events_recorded"]]
    assert "case_needs_review" in event_types_review


def test_ordinary_valid_case_completes_successfully():
    """
    Verify that an ordinary valid case within Tier 1 threshold (< ₹5,000.00 like ORD-2026-005)
    with non-conflicting policy evidence and passing verification completes autonomously:
    status='completed', needs_review=False, requires_supervisor_approval=False.
    """
    res = run_resolution_workflow(
        complaint_text="My USB-C docking station delivered in order ORD-2026-005 has a broken HDMI port.",
        order_number="ORD-2026-005",
        category="electronics",
    )

    assert res["workflow_status"] == "completed"
    assert res["needs_review"] is False
    assert res["requires_supervisor_approval"] is False
    assert res["requires_human_approval"] is False
    assert res["verification_result"]["is_valid"] is True
    assert "workflow_completed" in [e["event_type"] for e in res["events_recorded"]]


def test_api_and_case_events_agree_on_status(api_client):
    """
    Verify that the API response and case-event records agree on the final workflow status:
    1. For a review-required order (ORD-2026-001), response.status is 'needs_review'
       and the last workflow event is 'case_needs_review'.
    2. For a completed order (ORD-2026-005), response.status is 'completed'
       and the last workflow event is 'workflow_completed'.
    """
    # 1. Review-required case
    resp_review = api_client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "The laptop delivered in order ORD-2026-001 has a shattered display.",
            "order_number": "ORD-2026-001",
            "category": "electronics",
        },
    )
    assert resp_review.status_code == 200
    data_review = resp_review.json()
    assert data_review["status"] == "needs_review"
    review_events = [e["event_type"] for e in data_review["events_recorded"]]
    assert "case_needs_review" in review_events
    assert "workflow_completed" not in review_events

    # 2. Completed case
    resp_comp = api_client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "My USB-C docking station delivered in order ORD-2026-005 has a broken HDMI port.",
            "order_number": "ORD-2026-005",
            "category": "electronics",
        },
    )
    assert resp_comp.status_code == 200
    data_comp = resp_comp.json()
    assert data_comp["status"] == "completed"
    assert data_comp["needs_review"] is False
    comp_events = [e["event_type"] for e in data_comp["events_recorded"]]
    assert "workflow_completed" in comp_events
    assert "case_needs_review" not in comp_events
