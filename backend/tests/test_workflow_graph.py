"""
Automated unit tests for ResolveAI Level 4 LangGraph Multi-Agent Workflow Orchestration.
Validates graph compilation, all conditional branches, recovery loops, and case event recording.
Runs 100% offline without external network calls or paid APIs.
"""

import pytest
from unittest.mock import patch

from app.workflows import (
    create_resolution_graph,
    get_resolution_graph,
    run_resolution_workflow,
)
from app.workflows.state import initialize_workflow_state
from app.schemas.agent_schemas import (
    ResolutionRecommendationResult,
    VerificationResult,
)


def test_graph_creation_and_compilation():
    """Verify that create_resolution_graph compiles with all 11 required nodes and edges."""
    graph = create_resolution_graph()
    assert graph is not None

    expected_nodes = [
        "initialize_case",
        "analyze_complaint",
        "investigate_order",
        "retrieve_policy_evidence",
        "recommend_resolution",
        "verify_resolution",
        "attempt_recovery",
        "handle_missing_information",
        "escalate_case",
        "record_resolution",
        "finalize_response",
    ]
    for node_name in expected_nodes:
        assert node_name in graph.nodes, f"Node '{node_name}' must be registered in graph"


def test_workflow_empty_complaint_short_circuit():
    """Verify that empty complaint text fails fast at initialization without running downstream nodes."""
    res = run_resolution_workflow(complaint_text="   ")
    assert res["workflow_status"] == "failed"
    assert res["current_stage"] == "finalized"
    assert "Customer complaint text is empty or missing." in res["errors"]
    assert res["complaint_analysis"] is None
    assert res["order_investigation"] is None


def test_workflow_missing_order_routes_to_needs_information():
    """Verify that an unknown or missing order routes to handle_missing_information."""
    res = run_resolution_workflow(
        complaint_text="My order ORD-9999-NOTFOUND has not arrived. Where is it?",
        order_number="ORD-9999-NOTFOUND",
    )

    assert res["workflow_status"] == "needs_information"
    assert res["order_investigation"] is not None
    assert res["order_investigation"]["order_exists"] is False
    assert len(res["missing_information"]) > 0
    assert any("order" in m.lower() for m in res["missing_information"])


def test_workflow_valid_electronics_order():
    """Verify that a valid electronics order traverses analysis, investigation, RAG, recommendation, and verification."""
    res = run_resolution_workflow(
        complaint_text="I received order ORD-2026-001 with broken display. Need replacement.",
        order_number="ORD-2026-001",
        category="electronics",
    )

    assert res["order_investigation"]["order_exists"] is True
    assert res["complaint_analysis"]["category"] == "damaged_product"
    assert len(res["retrieved_policy_passages"]) > 0
    assert res["recommended_resolution"] is not None
    assert res["verification_result"]["is_valid"] is True

    # High value or tier check (ORD-2026-001 is INR 14,999.00 -> exceeds Tier 1 5,000 INR)
    # Correctly routes to needs_review for supervisor sign-off
    assert res["workflow_status"] in ("completed", "needs_review")
    if res["requires_human_approval"]:
        assert res["workflow_status"] == "needs_review"


def test_workflow_fashion_category_preservation():
    """Verify that a fashion category complaint retrieves fashion policy evidence."""
    res = run_resolution_workflow(
        complaint_text="Order ORD-2026-002 size does not fit. Want exchange with tags intact.",
        order_number="ORD-2026-002",
        category="fashion",
    )

    assert res["order_investigation"]["order_exists"] is True
    assert res["category"] == "fashion"
    assert len(res["retrieved_policy_passages"]) > 0
    assert any("fashion" in p.get("document_name", "").lower() for p in res["retrieved_policy_passages"])


def test_workflow_home_appliances_seller_filter():
    """Verify home appliance order ORD-2026-003 retains seller SELLER-003 metadata."""
    res = run_resolution_workflow(
        complaint_text="Order ORD-2026-003 air conditioner has transit damage cooling issue.",
        order_number="ORD-2026-003",
        seller_id="SELLER-003",
        category="home_appliances",
    )

    assert res["order_investigation"]["order_exists"] is True
    assert res["seller_id"] == "SELLER-003"
    assert len(res["retrieved_policy_passages"]) > 0


def test_workflow_insufficient_policy_evidence_escalates():
    """Verify that a complaint lacking policy evidence routes to escalate_case."""
    with patch("app.agents.policy_retriever.PolicyRetrieverAgent.retrieve") as mock_retrieve:
        from app.schemas.agent_schemas import PolicyRetrievalResult

        mock_retrieve.return_value = PolicyRetrievalResult(
            query="quantum alien device",
            passages=[],
            found_relevant=False,
            retrieval_method="semantic_search",
            explanation="No matching policy passages found.",
            insufficient_evidence=True,
        )

        res = run_resolution_workflow(
            complaint_text="My order ORD-2026-001 has damaged item but no policy applies.",
            order_number="ORD-2026-001",
            category="electronics",
        )

        assert res["insufficient_evidence"] is True
        assert res["workflow_status"] == "needs_review"


def test_workflow_policy_precedence_conflict_escalates():
    """Verify that an unresolved policy conflict routes to escalate_case."""
    with patch("app.agents.policy_retriever.PolicyRetrieverAgent.retrieve") as mock_retrieve:
        from app.schemas.agent_schemas import PolicyRetrievalResult, PolicyPassageSchema

        mock_retrieve.return_value = PolicyRetrievalResult(
            query="return refund conflict",
            passages=[
                PolicyPassageSchema(document_name="doc1.md", passage="rule 1", matched_terms=[], line_number=1, policy_id="P1", scope="seller"),
                PolicyPassageSchema(document_name="doc2.md", passage="rule 2", matched_terms=[], line_number=2, policy_id="P2", scope="platform"),
            ],
            found_relevant=True,
            retrieval_method="semantic_search",
            explanation="Conflicting rules.",
            conflict_status="needs_review",
            needs_review=True,
            policy_ids=["P1", "P2"],
        )

        res = run_resolution_workflow(
            complaint_text="My order ORD-2026-001 has direct conflict.",
            order_number="ORD-2026-001",
        )

        assert res["policy_conflict_status"] == "needs_review"
        assert res["workflow_status"] == "needs_review"


def test_workflow_bounded_recovery_on_verification_failure():
    """
    Verify bounded recovery behavior:
    When verification fails on first pass, attempt_recovery adjusts the recommendation
    and retries verification without entering an infinite loop.
    """
    call_count = {"count": 0}

    original_verify = from_verifier = None
    from app.agents.verifier import VerifierAgent

    def mock_verify(self, input_data):
        call_count["count"] += 1
        if call_count["count"] == 1:
            # First attempt fails verification due to unverified execution claim
            return VerificationResult(
                verification_status="fail",
                is_valid=False,
                detected_issues=["Falsely claimed replacement was dispatched"],
                evidence_checked=["Order status"],
                missing_evidence=[],
                required_next_step="Halt resolution.",
            )
        # Second attempt passes after recovery sanitization
        return VerificationResult(
            verification_status="pass",
            is_valid=True,
            detected_issues=[],
            evidence_checked=["Sanitized review recommendation"],
            missing_evidence=[],
            required_next_step="Submit for supervisor review.",
        )

    with patch.object(VerifierAgent, "verify", mock_verify):
        res = run_resolution_workflow(
            complaint_text="Order ORD-2026-001 defective product replacement claim.",
            order_number="ORD-2026-001",
            category="electronics",
        )

        assert call_count["count"] == 2, "Recovery should have caused a second verification call"
        assert res["retry_count"] == 1, "Retry count must be exactly 1"
        assert res["workflow_status"] == "needs_review"


def test_workflow_infinite_loop_prevention_on_persistent_failure():
    """Verify that when verification fails repeatedly, retry limits stop execution cleanly at escalate_case."""
    from app.agents.verifier import VerifierAgent

    def persistent_fail_verify(self, input_data):
        return VerificationResult(
            verification_status="fail",
            is_valid=False,
            detected_issues=["Persistent unresolvable contradiction"],
            evidence_checked=[],
            missing_evidence=[],
            required_next_step="Halt.",
        )

    with patch.object(VerifierAgent, "verify", persistent_fail_verify):
        res = run_resolution_workflow(
            complaint_text="Order ORD-2026-001 issue.",
            order_number="ORD-2026-001",
            max_retries=1,
        )

        assert res["retry_count"] == 1, "Must not exceed max_retries=1"
        assert res["workflow_status"] == "needs_review", "Must terminate at escalate_case"
        assert res["current_stage"] in ("escalate_case", "supervisor_review", "finalized")


def test_workflow_records_events_when_case_id_provided():
    """Verify that case audit events are recorded when an existing case ID is provided."""
    res = run_resolution_workflow(
        complaint_text="Order ORD-2026-001 audio crackling issue.",
        order_number="ORD-2026-001",
        case_id=1,
    )

    events = res.get("events_recorded", [])
    assert len(events) >= 3, "Workflow must record multiple events for case tracking"
    event_types = [e["event_type"] for e in events]
    assert "workflow_started" in event_types
    assert "complaint_analyzed" in event_types
    assert "order_investigation_completed" in event_types
