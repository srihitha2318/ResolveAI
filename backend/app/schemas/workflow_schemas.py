"""
Pydantic schemas for ResolveAI Level 4 LangGraph Multi-Agent Workflow Orchestration.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent_schemas import (
    ComplaintAnalysisResult,
    OrderInvestigationResult,
    PolicyRetrievalResult,
    ResolutionRecommendationResult,
    VerificationResult,
)


class WorkflowResolveRequest(BaseModel):
    """Input payload for initiating autonomous complaint resolution workflow."""

    model_config = ConfigDict(extra="ignore")

    complaint_text: str = Field(..., description="Customer submitted complaint or question")
    order_number: Optional[str] = Field(None, description="Optional referenced order identifier (e.g. ORD-2026-0001)")
    case_number: Optional[str] = Field(None, description="Optional existing support case number (e.g. CAS-2026-0001)")
    case_id: Optional[int] = Field(None, description="Optional existing support case database ID")
    customer_id: Optional[int] = Field(None, description="Optional customer database ID")
    category: Optional[str] = Field(None, description="Optional product category hint (electronics, fashion, home_appliances, general_merchandise)")
    seller_id: Optional[str] = Field(None, description="Optional seller identifier (SELLER-001, SELLER-002, SELLER-003)")


class WorkflowResolveResponse(BaseModel):
    """Structured response returned by the multi-agent orchestration workflow."""

    model_config = ConfigDict(extra="ignore")

    workflow_id: str = Field(..., description="Unique workflow execution run identifier")
    thread_id: Optional[str] = Field(None, description="LangGraph checkpoint thread identifier")
    case_id: Optional[int] = Field(None, description="Database ID of associated support case")
    case_number: Optional[str] = Field(None, description="Case number of associated support case")
    status: str = Field(..., description="Workflow final status: 'completed', 'needs_information', 'needs_review', or 'failed'")
    current_stage: str = Field(..., description="Final or current execution node stage")
    complaint_analysis: Optional[ComplaintAnalysisResult] = Field(None, description="Complaint analysis facts")
    order_investigation: Optional[OrderInvestigationResult] = Field(None, description="Order investigation facts")
    policy_evidence: Optional[PolicyRetrievalResult] = Field(None, description="Retrieved policy passages and provenance")
    retrieval_method: Optional[str] = Field(None, description="Retrieval method used: 'semantic_search' or 'keyword_fallback'")
    recommended_resolution: Optional[ResolutionRecommendationResult] = Field(None, description="Proposed resolution recommendation")
    verification_result: Optional[VerificationResult] = Field(None, description="Independent verification evaluation")
    needs_review: bool = Field(False, description="Flagged for human supervisor review")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation or supervisor review")
    supervisor_decision: Optional[str] = Field(None, description="Supervisor decision if reviewed ('approved', 'rejected')")
    missing_information: List[str] = Field(default_factory=list, description="List of missing facts or required customer input")
    clarification_details: Optional[Dict[str, str]] = Field(None, description="Explanation of why each missing field is required")
    errors: List[str] = Field(default_factory=list, description="Sanitized error logs recorded during execution")
    retry_count: int = Field(0, description="Number of recovery attempts executed")
    events_recorded: List[Dict[str, Any]] = Field(default_factory=list, description="Audit events persisted to the database")
    created_at: str = Field(..., description="ISO timestamp of workflow initialization")
    updated_at: str = Field(..., description="ISO timestamp of workflow completion")


# ---------------------------------------------------------------------------
# Level 5: Human Approval Request and Decision Schemas
# ---------------------------------------------------------------------------

class ApprovalDecisionRequest(BaseModel):
    """Input payload for supervisor approval or rejection decision."""

    model_config = ConfigDict(extra="forbid")

    reviewer_id: str = Field(..., min_length=1, description="Authorized reviewer identifier (e.g. 'supervisor_alice')")
    reason: Optional[str] = Field(None, description="Reason or operational notes for the decision (required on rejection)")
    override_expired: bool = Field(default=False, description="Explicit senior-supervisor confirmation required to process expired approval requests")


class PendingApprovalItem(BaseModel):
    """Summary item representing a case pending supervisor approval."""

    id: int
    case_id: int
    case_number: Optional[str] = None
    order_number: Optional[str] = None
    customer_name: Optional[str] = None
    thread_id: Optional[str] = None
    requested_action: str
    status: str
    workflow_status: str
    justification: str
    proposed_resolution: Optional[str] = None
    policy_evidence: Optional[str] = None
    expires_at: Optional[str] = None
    sla_priority: Optional[str] = "standard"
    required_role: Optional[str] = "tier2_supervisor"
    is_expired: bool = False
    created_at: str
    updated_at: str


class PendingApprovalsResponse(BaseModel):
    """Paginated list response of pending approval requests."""

    total_count: int
    limit: int
    offset: int
    items: List[PendingApprovalItem]


class ApprovalDetailResponse(BaseModel):
    """Detailed operational context for inspecting a case pending supervisor approval."""

    id: int
    case_id: int
    case_number: Optional[str] = None
    thread_id: Optional[str] = None
    requested_action: str
    status: str
    workflow_status: str
    justification: str
    proposed_resolution: Optional[str] = None
    policy_evidence: Optional[str] = None
    reviewer_id: Optional[str] = None
    decision_reason: Optional[str] = None
    decision_timestamp: Optional[str] = None
    expires_at: Optional[str] = None
    sla_priority: Optional[str] = "standard"
    required_role: Optional[str] = "tier2_supervisor"
    is_expired: bool = False
    created_at: str
    updated_at: str
    case: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    customer: Optional[Dict[str, Any]] = None


class ApprovalDecisionResponse(BaseModel):
    """Result returned after recording and resuming a supervisor approval or rejection decision."""

    id: int
    case_id: int
    thread_id: str
    status: str
    workflow_status: str
    reviewer_id: str
    decision_reason: Optional[str] = None
    decision_timestamp: str
    is_expired_override: Optional[bool] = False
    workflow_result: Optional[WorkflowResolveResponse] = None


# ---------------------------------------------------------------------------
# Level 6 Phase 3: Customer Clarification Loop Schemas
# ---------------------------------------------------------------------------

class ProvideInformationRequest(BaseModel):
    """
    Input payload for submitting customer clarification to resume a paused workflow.
    Accepts explicitly defined, validated fields.
    Forbids internal reviewer, role, approval, or execution fields.
    """

    model_config = ConfigDict(extra="forbid")

    order_number: Optional[str] = Field(
        None,
        min_length=1,
        max_length=64,
        description="Clarified or corrected order identifier (e.g. ORD-2026-001)",
    )
    additional_details: Optional[str] = Field(
        None,
        min_length=1,
        max_length=2000,
        description="Customer explanation, defect description, or clarification text",
    )
    customer_id: Optional[int] = Field(
        None,
        ge=1,
        description="Customer database ID for ownership and identity verification",
    )
    customer_email: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        description="Customer email address for identity verification",
    )
    category: Optional[str] = Field(
        None,
        min_length=1,
        max_length=64,
        description="Optional category hint (electronics, fashion, home_appliances, general_merchandise)",
    )
    seller_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=64,
        description="Optional seller identifier",
    )


class ProvideInformationResponse(BaseModel):
    """
    Response returned after processing customer clarification and resuming workflow.
    Indicates whether execution completed, escalated for review, remains blocked, or requires more information.
    """

    model_config = ConfigDict(extra="ignore")

    thread_id: str = Field(..., description="Workflow thread identifier")
    case_id: Optional[int] = Field(None, description="Database ID of associated support case")
    status: str = Field(..., description="Clarification processing outcome: 'completed', 'needs_review', 'needs_information', or 'resumed'")
    workflow_status: str = Field(..., description="Current status of the workflow state machine")
    message: str = Field(..., description="Operational status message explaining the outcome")
    missing_information: List[str] = Field(default_factory=list, description="Remaining missing fields if still blocked")
    clarification_details: Optional[Dict[str, str]] = Field(None, description="Detailed explanation of remaining missing fields")
    workflow_result: Optional[WorkflowResolveResponse] = Field(None, description="Complete resolved workflow state")


# ---------------------------------------------------------------------------
# Level 6 Phase 4: Customer Clarification Queue Schemas
# ---------------------------------------------------------------------------

class PendingClarificationItem(BaseModel):
    """Item representing a workflow paused awaiting customer clarification."""

    thread_id: str
    case_id: Optional[int] = None
    case_number: Optional[str] = None
    order_number: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    complaint_text: Optional[str] = None
    status: str = "needs_information"
    workflow_status: str = "needs_information"
    missing_information: List[str] = Field(default_factory=list)
    clarification_details: Optional[Dict[str, str]] = None
    clarification_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PendingClarificationsResponse(BaseModel):
    """Paginated list of workflows paused awaiting customer clarification."""

    total_count: int
    limit: int
    offset: int
    items: List[PendingClarificationItem]


class ClarificationDetailResponse(BaseModel):
    """Detailed operational context for a workflow thread awaiting customer clarification."""

    thread_id: str
    case_id: Optional[int] = None
    case_number: Optional[str] = None
    order_number: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    complaint_text: Optional[str] = None
    status: str = "needs_information"
    workflow_status: str = "needs_information"
    missing_information: List[str] = Field(default_factory=list)
    clarification_details: Optional[Dict[str, str]] = None
    clarification_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    case: Optional[Dict[str, Any]] = None
    customer: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None


