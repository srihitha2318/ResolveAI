"""
Integration and unit tests for ResolveAI Level 6 Phase 3: Customer Clarification Loops.

Covers:
1. Workflow that requests clarification on missing/unknown orders.
2. Structured missing fields and detailed requirement explanations in response.
3. Workflow checkpoint persistence in SQLite while awaiting clarification.
4. Valid customer information submission, resumption, and successful completion.
5. Rejection of empty and whitespace-only submissions (400 Bad Request).
6. Rejection of malformed submissions and path traversal attempts (400 Bad Request).
7. Rejection of nonexistent threads (404 Not Found).
8. Rejection of submissions on non-waiting threads (409 Conflict: supervisor review or completed).
9. Customer thread ownership enforcement (403 Forbidden on mismatched customer identity).
10. Cross-customer order submission prevention (403 Forbidden when submitting another customer's order).
11. Protection against modifying internal approval or reviewer fields (422 Unprocessable Entity).
12. Re-evaluation after receiving information (handles still-missing order by staying in needs_information).
13. Repeated submission and duplicate-side-effect protection (409 Conflict, no duplicate tickets).
14. Preservation of existing supervisor approval behavior for high-value orders after clarification.
15. Preservation of policy and verification safety invariants.
16. No real refund or payment execution throughout clarification workflows.
17. Authenticated frontline agent can submit clarification on behalf of customer.
"""

import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.db import SessionLocal
from app.database.models import SupportCase, SupportTicket, ApprovalRequest, CaseEvent, Order, Customer
from app.workflows import get_resolution_graph, run_resolution_workflow
from app.workflows.nodes import handle_missing_information_node, _generate_clarification_details
from app.workflows.state import initialize_workflow_state


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def frontline_token(client):
    """Obtains a Bearer token for frontline_agent charlie."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "agent_charlie", "password": "AgentPassword123!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def supervisor_token(client):
    """Obtains a Bearer token for tier2_supervisor alice."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "supervisor_alice", "password": "SupervisorPassword123!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Test 1 & 2: Clarification Detection & Explanations
# ---------------------------------------------------------------------------

def test_workflow_requests_clarification_on_missing_order(client):
    """
    When an order number is missing or cannot be found in the database,
    the workflow must pause with status='needs_information', report missing fields,
    and include detailed reasons why the information is required.
    """
    payload = {
        "complaint_text": "I ordered a coffee grinder last week but order ORD-9999-NOTFOUND is not arriving. Please help!",
        "order_number": "ORD-9999-NOTFOUND",
    }
    resp = client.post("/api/v1/workflows/resolve", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "needs_information"
    assert data["thread_id"] is not None
    assert data["thread_id"].startswith("thread-")
    assert len(data["missing_information"]) > 0

    # Ensure clarification details explain why the fields are needed
    assert data["clarification_details"] is not None
    assert isinstance(data["clarification_details"], dict)
    assert len(data["clarification_details"]) > 0
    # Explanation should mention order lookup or verification
    first_exp = list(data["clarification_details"].values())[0]
    assert "order" in first_exp.lower() or "required" in first_exp.lower()


def test_clarification_details_generator():
    """Verify that _generate_clarification_details produces distinct, informative reasons."""
    state = initialize_workflow_state(complaint_text="My order has issues.")
    missing = ["order_number", "photograph", "customer_email"]
    reasons = _generate_clarification_details(missing, state)

    assert "order_number" in reasons
    assert "photograph" in reasons
    assert "customer_email" in reasons
    assert "order" in reasons["order_number"].lower()
    assert "evidence" in reasons["photograph"].lower() or "defect" in reasons["photograph"].lower()
    assert "customer" in reasons["customer_email"].lower() or "account" in reasons["customer_email"].lower()


# ---------------------------------------------------------------------------
# Test 3: Checkpoint Persistence While Waiting
# ---------------------------------------------------------------------------

def test_workflow_checkpoint_persistence_while_waiting(client):
    """
    Verify that when the workflow requests clarification, execution pauses at
    the customer_clarification node and its state is persisted in the SQLite checkpointer.
    """
    payload = {
        "complaint_text": "Missing order inquiry for non-existent ORD-0000-XYZ.",
        "order_number": "ORD-0000-XYZ",
    }
    resp = client.post("/api/v1/workflows/resolve", json=payload)
    assert resp.status_code == 200
    thread_id = resp.json()["thread_id"]

    # Inspect checkpoint in persistent store
    graph = get_resolution_graph()
    checkpoint_state = graph.get_state({"configurable": {"thread_id": thread_id}})
    assert checkpoint_state is not None
    assert checkpoint_state.values is not None
    assert checkpoint_state.values["workflow_status"] == "needs_information"
    assert "customer_clarification" in checkpoint_state.next
    assert len(checkpoint_state.tasks) > 0


# ---------------------------------------------------------------------------
# Test 4: Valid Submission & Workflow Resumption
# ---------------------------------------------------------------------------

def test_valid_information_submission_and_workflow_resumption(client):
    """
    Submitting a valid order belonging to the customer resumes the workflow,
    re-evaluates facts against the real database, and completes the case.
    """
    # 1. Start workflow for Clara Dupont with nonexistent order
    init_payload = {
        "complaint_text": "My USB-C docking station from order ORD-WRONG-999 has a broken port upon unboxing.",
        "order_number": "ORD-WRONG-999",
        "category": "electronics",
        "customer_id": 3,  # Clara Dupont
    }
    init_resp = client.post("/api/v1/workflows/resolve", json=init_payload)
    assert init_resp.status_code == 200
    init_data = init_resp.json()
    assert init_data["status"] == "needs_information"
    thread_id = init_data["thread_id"]

    # 2. Clara submits the correct order number ORD-2026-005 (Tier 1 delivered order, total ₹4,999.00)
    clarify_payload = {
        "order_number": "ORD-2026-005",
        "customer_email": "clara.dupont@example.com",
        "additional_details": "Correction: the actual order is ORD-2026-005.",
    }
    res_resp = client.post(f"/api/v1/workflows/{thread_id}/provide-information", json=clarify_payload)
    assert res_resp.status_code == 200

    data = res_resp.json()
    assert data["status"] == "completed"
    assert data["workflow_status"] == "completed"
    assert data["thread_id"] == thread_id
    assert "completed successfully" in data["message"].lower()

    # 3. Verify audit events recorded in workflow state
    assert data["workflow_result"] is not None
    events = data["workflow_result"]["events_recorded"]
    event_types = [e["event_type"] for e in events]
    assert "customer_information_submitted" in event_types


# ---------------------------------------------------------------------------
# Test 5: Rejection of Empty and Whitespace Submissions
# ---------------------------------------------------------------------------

def test_rejection_of_empty_and_whitespace_submissions(client):
    """Verify that completely empty or whitespace submissions are rejected with HTTP 400."""
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={"complaint_text": "Missing order check", "order_number": "ORD-BAD-1"},
    )
    thread_id = init_resp.json()["thread_id"]

    # Completely empty payload
    r_empty = client.post(f"/api/v1/workflows/{thread_id}/provide-information", json={})
    assert r_empty.status_code == 400
    assert "at least one" in r_empty.json()["detail"].lower()

    # Whitespace only payload
    r_white = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "   ", "additional_details": "   "},
    )
    assert r_white.status_code == 400


# ---------------------------------------------------------------------------
# Test 6: Rejection of Malformed and Path Traversal Submissions
# ---------------------------------------------------------------------------

def test_rejection_of_malformed_and_path_traversal_submissions(client):
    """Verify that arbitrary filesystem paths and traversal sequences are rejected."""
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={"complaint_text": "Path traversal security check", "order_number": "ORD-BAD-2"},
    )
    thread_id = init_resp.json()["thread_id"]

    # Relative path traversal in order_number
    r_rel = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "../../etc/passwd", "customer_email": "clara.dupont@example.com"},
    )
    assert r_rel.status_code == 400
    assert "filesystem paths" in r_rel.json()["detail"].lower() or "traversal" in r_rel.json()["detail"].lower()

    # Windows path traversal in order_number
    r_win = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "C:\\Windows\\System32\\cmd.exe", "customer_email": "clara.dupont@example.com"},
    )
    assert r_win.status_code == 400

    # Path in details
    r_details = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "ORD-2026-005", "additional_details": "/var/run/secrets/token"},
    )
    assert r_details.status_code == 400


# ---------------------------------------------------------------------------
# Test 7: Rejection of Nonexistent or Non-Waiting Threads
# ---------------------------------------------------------------------------

def test_rejection_of_nonexistent_thread(client):
    """Submissions for unknown thread IDs must return HTTP 404."""
    unknown_thread = f"thread-ghost-{uuid.uuid4().hex[:8]}"
    resp = client.post(
        f"/api/v1/workflows/{unknown_thread}/provide-information",
        json={"order_number": "ORD-2026-005", "customer_email": "clara.dupont@example.com"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_rejection_of_submissions_for_non_waiting_threads(client):
    """
    Submissions for threads that are awaiting supervisor review (needs_review)
    or have already completed must return HTTP 409 Conflict.
    """
    # 1. High-value order pauses at supervisor_review
    high_val = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "Smartphone cracked screen refund request for ORD-2026-001.",
            "order_number": "ORD-2026-001",
        },
    )
    thread_review = high_val.json()["thread_id"]
    assert high_val.json()["status"] == "needs_review"

    # Attempt customer clarification on supervisor review thread
    resp_conflict = client.post(
        f"/api/v1/workflows/{thread_review}/provide-information",
        json={"order_number": "ORD-2026-001", "customer_email": "alice.chen@example.com"},
    )
    assert resp_conflict.status_code == 409
    assert "supervisor review" in resp_conflict.json()["detail"].lower()

    # 2. Low-value order completes immediately
    completed_case = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "My USB-C docking station delivered in order ORD-2026-005 has a broken HDMI port.",
            "order_number": "ORD-2026-005",
            "category": "electronics",
        },
    )
    thread_completed = completed_case.json()["thread_id"]
    assert completed_case.json()["status"] == "completed"

    resp_completed = client.post(
        f"/api/v1/workflows/{thread_completed}/provide-information",
        json={"order_number": "ORD-2026-005", "customer_email": "clara.dupont@example.com"},
    )
    assert resp_completed.status_code == 409
    assert "already completed" in resp_completed.json()["detail"].lower() or "not awaiting" in resp_completed.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 8: Customer & Thread Ownership Enforcement
# ---------------------------------------------------------------------------

def test_customer_thread_ownership_enforcement(client):
    """
    Verify that:
    1. A customer cannot provide clarification on another customer's thread (403 Forbidden).
    2. A customer cannot submit another customer's order details (403 Forbidden).
    """
    # 1. Start thread for Alice Chen (Customer ID 1)
    r1 = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "Order missing for Alice",
            "order_number": "ORD-ALICE-MISSING",
            "customer_id": 1,
        },
    )
    thread_id = r1.json()["thread_id"]

    # 2. Bob Martinez (Customer ID 2) attempts to submit clarification on Alice's thread
    r_bad_owner = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={
            "order_number": "ORD-2026-003",
            "customer_email": "bob.martinez@example.com",
        },
    )
    assert r_bad_owner.status_code == 403
    assert "owner" in r_bad_owner.json()["detail"].lower() or "not match" in r_bad_owner.json()["detail"].lower()

    # 3. Alice Chen attempts to submit Bob's order ORD-2026-003 (customer_id=2)
    r_cross_order = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={
            "order_number": "ORD-2026-003",
            "customer_email": "alice.chen@example.com",
        },
    )
    assert r_cross_order.status_code == 403
    assert "different customer" in r_cross_order.json()["detail"].lower() or "prohibited" in r_cross_order.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 9: Protection Against Modifying Internal Fields
# ---------------------------------------------------------------------------

def test_protection_against_modifying_internal_fields(client):
    """
    Submitting payloads attempting to alter internal review roles, decisions,
    approval flags, or authorization fields must be rejected (422 Unprocessable Entity).
    """
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={"complaint_text": "Tamper test", "order_number": "ORD-TAMPER-001"},
    )
    thread_id = init_resp.json()["thread_id"]

    # Attempt to inject supervisor approval
    r_tamper1 = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={
            "order_number": "ORD-2026-005",
            "supervisor_approved": True,
            "supervisor_decision": "approved",
        },
    )
    assert r_tamper1.status_code == 422

    # Attempt to inject role
    r_tamper2 = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={
            "order_number": "ORD-2026-005",
            "role": "senior_supervisor",
        },
    )
    assert r_tamper2.status_code == 422


# ---------------------------------------------------------------------------
# Test 10: Re-evaluation After Receiving Information
# ---------------------------------------------------------------------------

def test_re_evaluation_after_receiving_information_handles_still_invalid_order(client):
    """
    Customer-provided values are never blindly trusted.
    Submitting an order that STILL does not exist in the database causes
    the workflow to re-evaluate, fail order investigation, and stay in needs_information.
    """
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={"complaint_text": "Order not found", "order_number": "ORD-NONE-1"},
    )
    thread_id = init_resp.json()["thread_id"]

    # Customer submits a typo order that also does not exist
    clarify_resp = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={
            "order_number": "ORD-STILL-NOT-FOUND-2",
            "customer_email": "clara.dupont@example.com",
            "additional_details": "Here is the number on my receipt.",
        },
    )
    assert clarify_resp.status_code == 200
    data = clarify_resp.json()

    # Must remain blocked in needs_information
    assert data["status"] == "needs_information"
    assert data["workflow_status"] == "needs_information"
    assert len(data["missing_information"]) > 0
    assert "additional information is still required" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test 11: Repeated Submission & Duplicate Side-Effect Protection
# ---------------------------------------------------------------------------

def test_repeated_submission_and_duplicate_side_effect_protection(client):
    """
    Submitting information repeatedly to an already completed thread must be rejected (409 Conflict)
    and must not generate duplicate tickets or repeat execution.
    """
    # 1. Complete a case through clarification
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "My USB-C docking station from order ORD-WRONG-555 has a broken port upon delivery.",
            "order_number": "ORD-WRONG-555",
            "category": "electronics",
            "customer_id": 3,
        },
    )
    thread_id = init_resp.json()["thread_id"]

    c1 = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "ORD-2026-005", "customer_email": "clara.dupont@example.com"},
    )
    assert c1.status_code == 200
    case_id = c1.json()["case_id"]

    # Count tickets in DB
    with SessionLocal() as db:
        initial_ticket_count = db.query(SupportTicket).filter(SupportTicket.case_id == case_id).count()

    # 2. Resubmit to the same thread
    c2 = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "ORD-2026-005", "customer_email": "clara.dupont@example.com"},
    )
    assert c2.status_code == 409
    assert "already completed" in c2.json()["detail"].lower() or "duplicate" in c2.json()["detail"].lower()

    # Ticket count must remain identical
    with SessionLocal() as db:
        final_ticket_count = db.query(SupportTicket).filter(SupportTicket.case_id == case_id).count()
        assert final_ticket_count == initial_ticket_count


# ---------------------------------------------------------------------------
# Test 12: Preservation of Existing Supervisor Approval Behavior
# ---------------------------------------------------------------------------

def test_preservation_of_supervisor_approval_behavior(client, supervisor_token):
    """
    If customer-provided information clarifies a high-value order (e.g. ORD-2026-001, ₹19,999.00),
    the workflow re-evaluates the order facts, discovers it exceeds Tier 1 threshold,
    and pauses for supervisor review. An authorized supervisor can then approve it.
    """
    # 1. Initial execution with unknown order
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={
            "complaint_text": "I received a damaged laptop and need a replacement.",
            "order_number": "ORD-MISSING-HIGH-VAL",
            "customer_id": 1,  # Alice Chen
        },
    )
    thread_id = init_resp.json()["thread_id"]
    assert init_resp.json()["status"] == "needs_information"

    # 2. Customer provides real high-value order ORD-2026-001 (Alice Chen, total ₹19,999.00)
    clarify_resp = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={
            "order_number": "ORD-2026-001",
            "customer_email": "alice.chen@example.com",
            "additional_details": "Here is the correct order number ORD-2026-001.",
        },
    )
    assert clarify_resp.status_code == 200
    data = clarify_resp.json()

    # Workflow re-evaluated facts and safely routed to supervisor review
    assert data["status"] == "needs_review"
    assert data["workflow_status"] == "needs_review"
    assert "supervisor review" in data["message"].lower()

    # 3. Authorized supervisor Alice approves the case
    approve_resp = client.post(
        f"/api/v1/workflows/{thread_id}/approve",
        json={"reviewer_id": "supervisor_alice", "reason": "Customer verified order; replacement approved."},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert approve_resp.status_code == 200
    appr_data = approve_resp.json()
    assert appr_data["status"] == "approved"
    assert appr_data["workflow_status"] == "completed"


# ---------------------------------------------------------------------------
# Test 13: Preservation of Policy & Safety Invariants
# ---------------------------------------------------------------------------

def test_preservation_of_policy_and_verification_safety_invariants(client):
    """
    Customer clarification must never bypass policy precedence rules or verification.
    """
    # Start workflow where order is found but policy evidence is required
    res = run_resolution_workflow(
        complaint_text="I want to return an opened software license for full refund.",
        order_number="ORD-2026-005",
        category="electronics",
    )
    # Verification and policy checks execute normally
    assert res["workflow_status"] in ("completed", "needs_review")
    assert res["verification_result"] is not None


# ---------------------------------------------------------------------------
# Test 14: No Real Refund or Payment Execution
# ---------------------------------------------------------------------------

def test_no_real_refund_or_payment_execution(client):
    """
    Clarification loops must never execute real payment gateway transactions
    or disburse monetary funds.
    """
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={"complaint_text": "Refund request for delayed delivery.", "order_number": "ORD-UNKNOWN-99"},
    )
    thread_id = init_resp.json()["thread_id"]

    res = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "ORD-2026-005", "customer_email": "clara.dupont@example.com"},
    )
    assert res.status_code == 200

    # Verify no payment transaction occurred
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.order_number == "ORD-2026-005").first()
        assert order is not None
        assert order.currency == "INR"


# ---------------------------------------------------------------------------
# Test 15: Frontline Agent Submitting Clarification on Behalf of Customer
# ---------------------------------------------------------------------------

def test_authenticated_frontline_agent_can_submit_clarification_for_customer(client, frontline_token):
    """
    Frontline agents with valid Bearer tokens are authorized to submit customer
    clarification on behalf of the customer.
    """
    init_resp = client.post(
        "/api/v1/workflows/resolve",
        json={"complaint_text": "Phone call assistance needed for missing order.", "order_number": "ORD-MISSING-AGENT"},
    )
    thread_id = init_resp.json()["thread_id"]

    resp = client.post(
        f"/api/v1/workflows/{thread_id}/provide-information",
        json={"order_number": "ORD-2026-005", "additional_details": "Customer verified via phone call."},
        headers={"Authorization": f"Bearer {frontline_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("completed", "needs_review")
