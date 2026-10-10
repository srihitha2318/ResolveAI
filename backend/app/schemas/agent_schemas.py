from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Complaint Analyzer Schemas
# ---------------------------------------------------------------------------

class ComplaintAnalysisInput(BaseModel):
    complaint_text: str = Field(..., description="Customer submitted complaint or question")
    order_number: Optional[str] = Field(None, description="Optional referenced order identifier")
    case_id: Optional[int] = Field(None, description="Optional existing case identifier")


class ComplaintAnalysisResult(BaseModel):
    category: str = Field(..., description="Classified category (e.g. delayed_delivery, damaged_product, refund_request)")
    main_issue: str = Field(..., description="Summary of the main customer issue")
    desired_outcome: Optional[str] = Field(None, description="Desired outcome requested by the customer")
    order_number: Optional[str] = Field(None, description="Extracted or confirmed order number")
    image_relevant: bool = Field(False, description="Whether visual evidence/image is relevant for this issue")
    additional_info_required: bool = Field(False, description="Whether additional customer info is required")
    analysis_method: str = Field("rule_based", description="Method used: 'rule_based' or 'llm'")
    limitations: Optional[str] = Field(None, description="Known limitations or caveats of the analysis")


# ---------------------------------------------------------------------------
# Order Investigation Schemas
# ---------------------------------------------------------------------------

class OrderInvestigationInput(BaseModel):
    order_number: Optional[str] = Field(None, description="Order identifier to investigate")
    case_number: Optional[str] = Field(None, description="Existing case identifier to locate order")


class OrderDetailsSchema(BaseModel):
    id: int
    order_number: str
    product_name: str
    order_status: str
    delivery_status: str
    order_date: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    delivered_at: Optional[str] = None
    total_amount: int = Field(..., description="Order total in integer paise (INR)")
    currency: str = Field("INR", description="Currency ISO code (INR)")
    customer_id: int
    seller_id: Optional[str] = Field(None, description="Fictional seller identifier (e.g. SELLER-001)")
    category: Optional[str] = Field(None, description="Product category (electronics, fashion, home_appliances, general_merchandise)")
    total_amount_formatted: Optional[str] = Field(None, description="Formatted amount in Indian Rupees (e.g. ₹1,499.00)")


class CaseSummarySchema(BaseModel):
    id: int
    case_number: str
    order_id: Optional[int] = None
    subject: str
    status: str
    priority: str
    created_at: Optional[str] = None


class OrderInvestigationResult(BaseModel):
    order_exists: bool = Field(..., description="Whether the order was found in the database")
    order_number: Optional[str] = Field(None, description="Order identifier investigated")
    order_details: Optional[OrderDetailsSchema] = Field(None, description="Detailed order facts")
    delivery_summary: Optional[str] = Field(None, description="Summary of the delivery status")
    previous_cases: List[CaseSummarySchema] = Field(default_factory=list, description="Historical customer support cases")
    refund_status: str = Field("not_recorded", description="Status of refund records: 'not_recorded' or 'unknown'")
    missing_information: List[str] = Field(default_factory=list, description="Missing facts or attributes")
    limitations: str = Field(..., description="Operational boundaries and limitations")


# ---------------------------------------------------------------------------
# Policy Retrieval Schemas
# ---------------------------------------------------------------------------

class PolicySearchInput(BaseModel):
    query: str = Field(..., description="Search query or complaint category")
    seller_id: Optional[str] = Field(None, description="Optional seller filter (SELLER-001, SELLER-002, SELLER-003)")
    category: Optional[str] = Field(None, description="Optional category filter")
    scope: Optional[str] = Field(None, description="Optional policy scope filter (platform, category, seller)")
    policy_version: Optional[str] = Field(None, description="Optional policy version filter")
    method: Optional[str] = Field(None, description="Optional retrieval method: 'semantic', 'keyword', or 'auto'")


class PolicyPassageSchema(BaseModel):
    document_name: str
    passage: str
    matched_terms: List[str] = Field(default_factory=list)
    line_number: Optional[int] = None
    policy_id: Optional[str] = None
    scope: Optional[str] = None


class PolicyRetrievalResult(BaseModel):
    query: str
    passages: List[PolicyPassageSchema] = Field(default_factory=list)
    found_relevant: bool = Field(False)
    retrieval_method: str = Field("keyword_search", description="Retrieval method used")
    explanation: str = Field(...)
    policy_ids: List[str] = Field(default_factory=list, description="IDs of cited policies")
    source_files: List[str] = Field(default_factory=list, description="Source files cited")
    conflict_status: Optional[str] = Field(None, description="Precedence resolution status")
    needs_review: bool = Field(False, description="Flagged for human supervisor review")
    insufficient_evidence: bool = Field(False, description="Whether policy evidence was insufficient")


# ---------------------------------------------------------------------------
# Resolution Recommendation Schemas
# ---------------------------------------------------------------------------

class ResolutionRecommendationInput(BaseModel):
    complaint_analysis: ComplaintAnalysisResult
    order_investigation: OrderInvestigationResult
    policy_evidence: PolicyRetrievalResult


class ResolutionRecommendationResult(BaseModel):
    recommendation_type: str = Field(..., description="e.g. explain_order_status, request_more_info, recommend_refund_review, recommend_replacement_review, escalate_to_human, insufficient_evidence")
    title: str = Field(...)
    reasoning: str = Field(...)
    action_required: str = Field(...)
    human_approval_required: bool = Field(False)
    missing_information: List[str] = Field(default_factory=list)
    evidence_used: List[str] = Field(default_factory=list)
    method: str = Field("rule_based", description="'rule_based' or 'llm'")


# ---------------------------------------------------------------------------
# Verification Schemas
# ---------------------------------------------------------------------------

class VerificationInput(BaseModel):
    recommendation: ResolutionRecommendationResult
    complaint_analysis: Optional[ComplaintAnalysisResult] = None
    order_investigation: Optional[OrderInvestigationResult] = None
    policy_evidence: Optional[PolicyRetrievalResult] = None


class VerificationResult(BaseModel):
    verification_status: str = Field(..., description="'pass' or 'fail'")
    is_valid: bool = Field(...)
    detected_issues: List[str] = Field(default_factory=list)
    evidence_checked: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    required_next_step: str = Field(...)


# ---------------------------------------------------------------------------
# Support Case Ticket / Event Write Schemas
# ---------------------------------------------------------------------------

class CreateTicketRequest(BaseModel):
    category: str = Field(..., description="Support ticket category")


class CreateEventRequest(BaseModel):
    event_type: str = Field(..., description="Case event type")
    message: str = Field(..., description="Audit message")
    details_json: Optional[str] = Field(None, description="Optional JSON details")


class CaseEventResponse(BaseModel):
    id: int = Field(..., description="Unique event database identifier")
    case_id: int = Field(..., description="Parent case database identifier")
    event_type: str = Field(..., description="Event classification")
    message: str = Field(..., description="Audit message description")
    details_json: Optional[str] = Field(None, description="Detailed JSON metadata")
    created_at: str = Field(..., description="ISO event recording timestamp")


class CaseEventsListResponse(BaseModel):
    case_id: int = Field(..., description="Support case database identifier")
    events: List[CaseEventResponse] = Field(default_factory=list, description="Chronological audit history events")

