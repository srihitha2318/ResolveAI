"""
Strongly typed state definition for ResolveAI Level 4 LangGraph Workflow Orchestration.
Follows LangGraph TypedDict conventions for deterministic, serializable state updates.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict
import uuid


class WorkflowState(TypedDict, total=False):
    """
    Typed state dictionary representing the full operational context of a customer support case
    as it transitions across multi-agent orchestration nodes.
    All fields are JSON-serializable to ensure checkpointing compatibility.
    """

    # Identifiers
    workflow_id: str
    thread_id: str  # LangGraph checkpoint thread identifier
    case_id: Optional[int]
    case_number: Optional[str]
    customer_id: Optional[int]
    order_id: Optional[int]
    order_number: Optional[str]
    category: Optional[str]
    seller_id: Optional[str]

    # Raw customer input
    customer_complaint: str

    # Agent step facts
    complaint_analysis: Optional[Dict[str, Any]]
    complaint_category: Optional[str]
    urgency: Optional[str]

    order_investigation: Optional[Dict[str, Any]]
    order_status: Optional[str]

    retrieved_policy_passages: List[Dict[str, Any]]
    policy_source_metadata: List[Dict[str, Any]]
    policy_ids: List[str]
    retrieval_method: Optional[str]
    policy_conflict_status: Optional[str]
    insufficient_evidence: bool

    recommended_resolution: Optional[Dict[str, Any]]
    verification_result: Optional[Dict[str, Any]]

    # Workflow lifecycle and routing controls
    workflow_status: str  # 'completed', 'needs_information', 'needs_review', 'failed'
    current_stage: str
    missing_information: List[str]
    clarification_details: Optional[Dict[str, str]]
    clarification_count: int
    missing_order: bool
    escalation_reason: Optional[str]
    requires_human_approval: bool
    requires_supervisor_approval: bool
    needs_review: bool
    supervisor_decision: Optional[str]  # 'approved', 'rejected', None
    supervisor_reviewer: Optional[str]
    supervisor_reason: Optional[str]
    supervisor_approved: bool
    errors: List[str]
    retry_count: int
    max_retries: int

    # Audit & telemetry
    events_recorded: List[Dict[str, Any]]
    created_at: str
    updated_at: str


def initialize_workflow_state(
    complaint_text: str,
    order_number: Optional[str] = None,
    case_number: Optional[str] = None,
    case_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    category: Optional[str] = None,
    seller_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    max_retries: int = 1,
) -> WorkflowState:
    """Initializes a fresh, valid WorkflowState dict with default values."""
    now_iso = datetime.now(timezone.utc).isoformat()
    wf_id = workflow_id or f"wf-{uuid.uuid4().hex[:12]}"
    th_id = thread_id or f"thread-{case_number or (f'case-{case_id}' if case_id else uuid.uuid4().hex[:12])}"

    return {
        "workflow_id": wf_id,
        "thread_id": th_id,
        "case_id": case_id,
        "case_number": case_number,
        "customer_id": customer_id,
        "order_id": None,
        "order_number": (order_number or "").strip() or None,
        "category": (category or "").strip() or None,
        "seller_id": (seller_id or "").strip() or None,
        "customer_complaint": complaint_text or "",
        "complaint_analysis": None,
        "complaint_category": None,
        "urgency": "medium",
        "order_investigation": None,
        "order_status": None,
        "missing_order": False,
        "retrieved_policy_passages": [],
        "policy_source_metadata": [],
        "policy_ids": [],
        "retrieval_method": None,
        "policy_conflict_status": None,
        "insufficient_evidence": False,
        "recommended_resolution": None,
        "verification_result": None,
        "workflow_status": "in_progress",
        "current_stage": "initialized",
        "missing_information": [],
        "clarification_details": None,
        "clarification_count": 0,
        "escalation_reason": None,
        "requires_human_approval": False,
        "requires_supervisor_approval": False,
        "needs_review": False,
        "supervisor_decision": None,
        "supervisor_reviewer": None,
        "supervisor_reason": None,
        "supervisor_approved": False,
        "errors": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "events_recorded": [],
        "created_at": now_iso,
        "updated_at": now_iso,
    }
