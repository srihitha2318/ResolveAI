"""
Unit tests for ResolveAI Level 4 WorkflowState and initialization.
Validates state structure, schema defaults, and JSON serializability.
"""

import json
from app.workflows.state import WorkflowState, initialize_workflow_state


def test_workflow_state_initialization_defaults():
    """Verify that initialize_workflow_state populates all required fields with safe defaults."""
    state = initialize_workflow_state(
        complaint_text="My laptop screen has dead pixels upon unboxing.",
        order_number="ORD-2026-001",
        category="electronics",
        seller_id="SELLER-001",
    )

    assert state["workflow_id"].startswith("wf-")
    assert state["customer_complaint"] == "My laptop screen has dead pixels upon unboxing."
    assert state["order_number"] == "ORD-2026-001"
    assert state["category"] == "electronics"
    assert state["seller_id"] == "SELLER-001"
    assert state["workflow_status"] == "in_progress"
    assert state["current_stage"] == "initialized"
    assert state["retry_count"] == 0
    assert state["max_retries"] == 1
    assert state["events_recorded"] == []
    assert state["errors"] == []
    assert state["requires_human_approval"] is False
    assert state["requires_supervisor_approval"] is False
    assert state["needs_review"] is False
    assert state["missing_order"] is False
    assert state["insufficient_evidence"] is False


def test_workflow_state_json_serializability():
    """Verify that WorkflowState can be serialized to JSON without custom object errors."""
    state = initialize_workflow_state(
        complaint_text="Test complaint",
        order_number="ORD-2026-002",
        case_id=1,
    )
    state["complaint_analysis"] = {"category": "damaged_product", "main_issue": "damaged"}
    state["retrieved_policy_passages"] = [{"doc": "policy.md", "passage": "text"}]

    serialized = json.dumps(state)
    assert isinstance(serialized, str)
    deserialized = json.loads(serialized)
    assert deserialized["workflow_id"] == state["workflow_id"]
    assert deserialized["complaint_analysis"]["category"] == "damaged_product"


def test_workflow_state_empty_complaint_handling():
    """Verify that an empty complaint text is cleanly handled in initial state."""
    state = initialize_workflow_state(complaint_text="")
    assert state["customer_complaint"] == ""
    assert state["order_number"] is None
