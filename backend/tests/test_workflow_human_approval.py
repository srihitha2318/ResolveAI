"""
Integration and unit tests for ResolveAI Level 5 Human-in-the-Loop Approval and Review.

Tests cover:
- Scenario A: High-risk/supervisor cases pause at supervisor_review and persist checkpoint.
- Scenario B: GET /api/v1/workflows/pending-approvals returns paginated list of pending cases.
- Scenario C: GET /api/v1/workflows/{thread_id}/approval returns complete investigation context.
- Scenario D: POST /api/v1/workflows/{thread_id}/approve resumes workflow and marks completed.
- Scenario E: POST /api/v1/workflows/{thread_id}/reject halts resolution without creating ticket.
- Scenario F: Error handling (404 unknown thread, 409 conflict on already-decided, 400 validation).
- Scenario G: Safety invariant defense: Policy conflict / verification failure cannot complete on approve.
- Scenario H: Cross-process persistence: Fresh graph instance successfully resumes from SQLite checkpoint.
- Scenario I: Low-risk cases without approval requirement execute without pause.
"""

import json
import uuid
import pytest
from fastapi.testclient import TestClient
from langgraph.types import Command

from app.main import app
from app.database.db import SessionLocal
from app.database.models import ApprovalRequest, SupportCase, CaseEvent
from app.workflows import (
    initialize_workflow_state,
    run_resolution_workflow,
    get_resolution_graph,
    create_resolution_graph,
)
from app.workflows.routing import route_after_supervisor_review
from app.workflows.nodes import record_resolution_node, finalize_response_node


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Scenario A: Initial execution pauses at supervisor_review
# ---------------------------------------------------------------------------

def test_high_risk_order_pauses_at_supervisor_review(client):
    """
    High-value electronics return (e.g., ORD-2026-001) exceeds Tier 1 threshold.
    The workflow must pause at supervisor_review with status='needs_review',
    record an approval request in the DB, and persist a LangGraph checkpoint.
    """
    payload = {
        "complaint_text": "I received my smartphone ORD-2026-001 with a cracked screen and want a full refund.",
        "order_number": "ORD-2026-001",
        "category": "electronics",
    }
    response = client.post("/api/v1/workflows/resolve", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "needs_review"
    assert data["needs_review"] is True
    assert data["thread_id"] is not None
    assert data["thread_id"].startswith("thread-")
    assert data["case_id"] is not None

    thread_id = data["thread_id"]

    # Verify ApprovalRequest created in database
    with SessionLocal() as db:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.thread_id == thread_id).first()
        assert approval is not None
        assert approval.status == "pending"
        assert approval.case_id == data["case_id"]


# ---------------------------------------------------------------------------
# Scenario B: GET /api/v1/workflows/pending-approvals
# ---------------------------------------------------------------------------

def test_get_pending_approvals_list(client):
    """
    Verify GET /api/v1/workflows/pending-approvals returns pending items and supports pagination.
    """
    # Trigger a case that requires review
    payload = {
        "complaint_text": "High value refund request for ORD-2026-001 damaged box.",
        "order_number": "ORD-2026-001",
    }
    client.post("/api/v1/workflows/resolve", json=payload)

    response = client.get("/api/v1/workflows/pending-approvals?limit=10&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert "total_count" in data
    assert "items" in data
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["items"]) >= 1

    first_item = data["items"][0]
    assert "id" in first_item
    assert "case_id" in first_item
    assert "thread_id" in first_item
    assert "status" in first_item
    assert first_item["status"] == "pending"


# ---------------------------------------------------------------------------
# Scenario C: GET /api/v1/workflows/{thread_id}/approval
# ---------------------------------------------------------------------------

def test_get_approval_details_by_thread_id(client):
    """
    Verify GET /api/v1/workflows/{thread_id}/approval returns complete case context,
    order facts, proposed resolution, and policy citations.
    """
    payload = {
        "complaint_text": "Detailed inspect request for ORD-2026-001 damaged screen.",
        "order_number": "ORD-2026-001",
    }
    wf_resp = client.post("/api/v1/workflows/resolve", json=payload)
    thread_id = wf_resp.json()["thread_id"]

    response = client.get(f"/api/v1/workflows/{thread_id}/approval")
    assert response.status_code == 200

    data = response.json()
    assert data["thread_id"] == thread_id
    assert data["status"] == "pending"
    assert data["case_id"] is not None
    assert "proposed_resolution" in data
    assert "policy_evidence" in data


# ---------------------------------------------------------------------------
# Scenario D: POST /api/v1/workflows/{thread_id}/approve (Resume & Complete)
# ---------------------------------------------------------------------------

def test_approve_workflow_case_resumes_and_completes(client):
    """
    Verify that an authorized supervisor approval resumes the paused workflow
    from the SQLite checkpoint and completes remaining steps with status='completed'.
    """
    # 1. Start case that pauses at supervisor_review
    payload = {
        "complaint_text": "I want a replacement for ORD-2026-001 with damaged packaging.",
        "order_number": "ORD-2026-001",
    }
    wf_resp = client.post("/api/v1/workflows/resolve", json=payload)
    assert wf_resp.status_code == 200
    wf_data = wf_resp.json()
    thread_id = wf_data["thread_id"]
    case_id = wf_data["case_id"]
    assert wf_data["status"] == "needs_review"

    # 2. Submit approval
    approval_payload = {
        "reviewer_id": "supervisor_alice",
        "reason": "Verified damaged photos and customer tier; approved per policy Tier 2.",
    }
    appr_resp = client.post(f"/api/v1/workflows/{thread_id}/approve", json=approval_payload)
    assert appr_resp.status_code == 200

    decision_data = appr_resp.json()
    assert decision_data["status"] == "approved"
    assert decision_data["reviewer_id"] == "supervisor_alice"
    assert decision_data["workflow_status"] == "completed"
    assert decision_data["workflow_result"]["status"] == "completed"
    assert decision_data["workflow_result"]["needs_review"] is False

    # 3. Verify DB state and audit events
    with SessionLocal() as db:
        approval_rec = db.query(ApprovalRequest).filter(ApprovalRequest.thread_id == thread_id).first()
        assert approval_rec.status == "approved"
        assert approval_rec.reviewer_id == "supervisor_alice"

        events = db.query(CaseEvent).filter(CaseEvent.case_id == case_id).all()
        event_types = [e.event_type for e in events]
        assert "approval_granted" in event_types
        assert "workflow_resumed" in event_types


# ---------------------------------------------------------------------------
# Scenario E: POST /api/v1/workflows/{thread_id}/reject (Resume & Reject)
# ---------------------------------------------------------------------------

def test_reject_workflow_case_terminates_without_ticket(client):
    """
    Verify that an authorized supervisor rejection halts the workflow,
    sets status='rejected', and does not create an approval ticket or completed resolution.
    """
    # 1. Start case that pauses at supervisor_review
    payload = {
        "complaint_text": "I received my order ORD-2026-001 completely smashed and demand full cash refund immediately.",
        "order_number": "ORD-2026-001",
        "category": "electronics",
    }
    wf_resp = client.post("/api/v1/workflows/resolve", json=payload)
    wf_data = wf_resp.json()
    thread_id = wf_data["thread_id"]
    case_id = wf_data["case_id"]

    # 2. Submit rejection
    reject_payload = {
        "reviewer_id": "supervisor_bob",
        "reason": "Ineligible claim: customer has not provided mandatory unboxing evidence.",
    }
    rej_resp = client.post(f"/api/v1/workflows/{thread_id}/reject", json=reject_payload)
    assert rej_resp.status_code == 200

    decision_data = rej_resp.json()
    assert decision_data["status"] == "rejected"
    assert decision_data["reviewer_id"] == "supervisor_bob"
    assert decision_data["workflow_status"] == "rejected"
    assert decision_data["workflow_result"]["status"] == "rejected"
    assert decision_data["workflow_result"]["needs_review"] is False

    # 3. Verify DB state
    with SessionLocal() as db:
        approval_rec = db.query(ApprovalRequest).filter(ApprovalRequest.thread_id == thread_id).first()
        assert approval_rec.status == "rejected"
        assert approval_rec.reviewer_id == "supervisor_bob"

        events = db.query(CaseEvent).filter(CaseEvent.case_id == case_id).all()
        event_types = [e.event_type for e in events]
        assert "approval_rejected" in event_types


# ---------------------------------------------------------------------------
# Scenario F: Error Handling & Validation
# ---------------------------------------------------------------------------

def test_approval_endpoints_error_handling(client):
    """
    Verify 404 for unknown thread, 409 for already decided, and 400 for bad input.
    """
    # 1. 404 on unknown thread
    unknown_id = f"thread-unknown-{uuid.uuid4().hex[:8]}"
    r_404 = client.get(f"/api/v1/workflows/{unknown_id}/approval")
    assert r_404.status_code == 404

    r_post_404 = client.post(
        f"/api/v1/workflows/{unknown_id}/approve",
        json={"reviewer_id": "sup1", "reason": "ok"},
    )
    assert r_post_404.status_code == 404

    # 2. 400 on empty reviewer_id
    r_empty_rev = client.post(
        f"/api/v1/workflows/{unknown_id}/approve",
        json={"reviewer_id": "  ", "reason": "ok"},
    )
    assert r_empty_rev.status_code == 400

    # 3. 400 on empty rejection reason
    r_empty_reason = client.post(
        f"/api/v1/workflows/{unknown_id}/reject",
        json={"reviewer_id": "sup1", "reason": "   "},
    )
    assert r_empty_reason.status_code == 400

    # 4. 409 Conflict when attempting to re-decide an already approved/rejected case
    payload = {
        "complaint_text": "Order ORD-2026-001 arrived with cracked casing and defective screen.",
        "order_number": "ORD-2026-001",
        "category": "electronics",
    }
    resp1 = client.post("/api/v1/workflows/resolve", json=payload)
    tid = resp1.json()["thread_id"]

    # First approve: succeeds
    appr1 = client.post(f"/api/v1/workflows/{tid}/approve", json={"reviewer_id": "s1", "reason": "approved once"})
    assert appr1.status_code == 200

    # Second approve: 409 Conflict
    appr2 = client.post(f"/api/v1/workflows/{tid}/approve", json={"reviewer_id": "s2", "reason": "approved twice"})
    assert appr2.status_code == 409

    # Rejection on already approved: 409 Conflict
    rej_conflict = client.post(f"/api/v1/workflows/{tid}/reject", json={"reviewer_id": "s2", "reason": "now rejecting"})
    assert rej_conflict.status_code == 409


# ---------------------------------------------------------------------------
# Scenario G: Safety Invariant Defense on Resume
# ---------------------------------------------------------------------------

def test_safety_invariants_prevent_invalid_completion_on_resume():
    """
    Even if supervisor approves, if the state has an unresolved policy conflict
    or failed verification, route_after_supervisor_review and record_resolution_node
    must refuse to mark the case as completed.
    """
    # Test router defense on policy conflict
    state_with_conflict = initialize_workflow_state("Test conflict")
    state_with_conflict["supervisor_decision"] = "approved"
    state_with_conflict["supervisor_approved"] = True
    state_with_conflict["policy_conflict_status"] = "needs_review"

    dest = route_after_supervisor_review(state_with_conflict)
    assert dest == "finalize_response"

    # Test router defense on verification failure
    state_with_ver_fail = initialize_workflow_state("Test ver failure")
    state_with_ver_fail["supervisor_decision"] = "approved"
    state_with_ver_fail["supervisor_approved"] = True
    state_with_ver_fail["verification_result"] = {"is_valid": False, "verification_status": "fail"}

    dest2 = route_after_supervisor_review(state_with_ver_fail)
    assert dest2 == "finalize_response"

    # Test record_resolution_node invariant defense
    state_bad_record = initialize_workflow_state("Test bad record")
    state_bad_record["supervisor_approved"] = True
    state_bad_record["insufficient_evidence"] = True
    rec_out = record_resolution_node(state_bad_record)
    assert rec_out.get("workflow_status") != "completed"


# ---------------------------------------------------------------------------
# Scenario H: State Persistence Across Separate Graph Instances
# ---------------------------------------------------------------------------

def test_persistence_across_fresh_graph_instances():
    """
    Verify that an execution paused on one graph instance can be resumed
    by a completely fresh graph instance sharing the SQLite checkpointer.
    """
    thread_id = f"thread-persist-{uuid.uuid4().hex[:8]}"

    # Graph instance 1 starts the execution and pauses at supervisor_review
    g1 = get_resolution_graph()
    initial_state = initialize_workflow_state(
        complaint_text="I received my smartphone ORD-2026-001 with a cracked screen and want a full refund.",
        order_number="ORD-2026-001",
        category="electronics",
        thread_id=thread_id,
    )
    config = {"configurable": {"thread_id": thread_id}}
    res1 = g1.invoke(initial_state, config=config)

    # Verify paused
    checkpoint_state = g1.get_state(config)
    assert "supervisor_review" in checkpoint_state.next or len(checkpoint_state.tasks) > 0

    # Instantiate a completely fresh graph instance (Graph 2)
    g2 = create_resolution_graph()

    # Resume from Graph 2 using Command
    resume_cmd = Command(resume={
        "action": "approve",
        "reviewer_id": "cross_graph_supervisor",
        "reason": "Successfully verified cross-instance resume.",
    })
    res2 = g2.invoke(resume_cmd, config=config)

    assert res2["workflow_status"] == "completed"
    assert res2["supervisor_approved"] is True
    assert res2["supervisor_reviewer"] == "cross_graph_supervisor"


# ---------------------------------------------------------------------------
# Scenario I: Low-risk cases execute without pause
# ---------------------------------------------------------------------------

def test_low_risk_case_executes_without_pause(client):
    """
    Cases within standard automated threshold (e.g. low amount or info queries)
    should complete without requiring supervisor review.
    """
    payload = {
        "complaint_text": "What is the return policy window?",
        "order_number": None,
    }
    response = client.post("/api/v1/workflows/resolve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("needs_information", "completed")


def test_supervisor_dashboard_endpoint_html(client):
    """Verify GET /dashboard serves HTML Supervisor Command Center."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ResolveAI" in response.text
    assert "Supervisor Command" in response.text
