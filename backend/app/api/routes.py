import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from langgraph.types import Command

_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.config import settings
from app.core.logging_config import logger
from app.database.db import get_db, check_db_connection
from app.schemas.status import StatusResponse
from app.schemas.agent_schemas import (
    ComplaintAnalysisInput,
    ComplaintAnalysisResult,
    OrderInvestigationInput,
    OrderInvestigationResult,
    PolicySearchInput,
    PolicyRetrievalResult,
    ResolutionRecommendationInput,
    ResolutionRecommendationResult,
    VerificationInput,
    VerificationResult,
    CreateTicketRequest,
    CreateEventRequest,
    CaseEventResponse,
    CaseEventsListResponse,
    PolicyPassageSchema,
)
from app.schemas.customer_schemas import (
    CustomerVerifyAccessRequest,
    CustomerAccessResponse,
    CustomerCaseSummary,
    CustomerCaseDetail,
)
from app.schemas.analytics_schemas import AnalyticsOverviewResponse
from app.schemas.workflow_schemas import (
    WorkflowResolveRequest,
    WorkflowResolveResponse,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    PendingApprovalItem,
    PendingApprovalsResponse,
    ApprovalDetailResponse,
    ProvideInformationRequest,
    ProvideInformationResponse,
    PendingClarificationItem,
    PendingClarificationsResponse,
    ClarificationDetailResponse,
)
from app.schemas.auth_schemas import LoginRequest, TokenResponse, UserResponse
from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_user_optional,
    get_approval_reviewer,
    AuthenticatedReviewer,
    is_role_authorized_for_approval,
    is_role_authorized_for_rejection,
    ROLE_SENIOR_SUPERVISOR,
    ROLE_CUSTOMER,
    create_customer_token,
    get_current_customer,
    AuthenticatedCustomer,
)
from app.core.sla import validate_approval_decision_sla, evaluate_and_record_sla_breach
from app.database.models import User, ApprovalRequest, Customer, Order, SupportCase, SupportTicket
from app.workflows import run_resolution_workflow, get_resolution_graph
from app.agents import (
    ComplaintAnalyzerAgent,
    OrderInvestigatorAgent,
    PolicyRetrieverAgent,
    ResolutionRecommenderAgent,
    VerifierAgent,
)
from app.tools.support_tools import (
    get_order_details,
    get_case_details,
    create_support_ticket,
    record_case_event,
    get_pending_approval_requests,
    get_approval_request_by_thread_id,
    record_approval_decision,
    get_pending_clarifications,
    get_clarification_by_thread_id,
    get_case_events,
    get_analytics_summary,
)

api_router = APIRouter()


# ---------------------------------------------------------------------------
# System Status Probe (Preserved from Level 1)
# ---------------------------------------------------------------------------

@api_router.get(
    "/status",
    response_model=StatusResponse,
    summary="Detailed system status and database health",
    tags=["system"]
)
def get_system_status(
    response: Response,
    db: Session = Depends(get_db)
) -> StatusResponse:
    """
    Returns operational status of the service and verifies database connectivity.
    If database check fails, status code 503 is returned.
    """
    is_db_connected = check_db_connection(db)

    if not is_db_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StatusResponse(
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.APP_ENV,
            database="disconnected",
            message="Database connectivity failure",
        )

    return StatusResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database="connected",
        message="All subsystems operational",
    )


# ---------------------------------------------------------------------------
# AI Agent Endpoints (Level 2)
# ---------------------------------------------------------------------------

@api_router.post(
    "/analyze-complaint",
    response_model=ComplaintAnalysisResult,
    summary="Analyze and categorize customer complaint",
    tags=["agents"]
)
def analyze_complaint(payload: ComplaintAnalysisInput) -> ComplaintAnalysisResult:
    """Analyzes customer complaint text and extracts relevant attributes."""
    agent = ComplaintAnalyzerAgent()
    return agent.analyze(payload)


@api_router.post(
    "/investigate-order",
    response_model=OrderInvestigationResult,
    summary="Investigate stored order details and customer history",
    tags=["agents"]
)
def investigate_order(
    payload: OrderInvestigationInput,
    db: Session = Depends(get_db)
) -> OrderInvestigationResult:
    """Investigates stored order state, delivery status, and prior cases using real database tools."""
    agent = OrderInvestigatorAgent()
    return agent.investigate(db, payload)


@api_router.post(
    "/search-policies",
    response_model=PolicyRetrievalResult,
    summary="Search local support policies for relevant passages",
    tags=["agents"]
)
def search_policies(payload: PolicySearchInput) -> PolicyRetrievalResult:
    """Retrieves relevant passages from stored policy documents using semantic vector search with keyword fallback."""
    agent = PolicyRetrieverAgent()
    return agent.retrieve(payload)


@api_router.post(
    "/recommend-resolution",
    response_model=ResolutionRecommendationResult,
    summary="Recommend a customer support resolution based on evidence",
    tags=["agents"]
)
def recommend_resolution(payload: ResolutionRecommendationInput) -> ResolutionRecommendationResult:
    """Generates an evidence-backed resolution recommendation."""
    agent = ResolutionRecommenderAgent()
    return agent.recommend(payload)


@api_router.post(
    "/verify-resolution",
    response_model=VerificationResult,
    summary="Verify proposed recommendation against factual constraints",
    tags=["agents"]
)
def verify_resolution(payload: VerificationInput) -> VerificationResult:
    """Independently verifies recommendation facts, citations, and authorization boundaries."""
    agent = VerifierAgent()
    return agent.verify(payload)


# ---------------------------------------------------------------------------
# Real Support Operational Endpoints (Level 2)
# ---------------------------------------------------------------------------

@api_router.get(
    "/orders/{order_number}",
    summary="Retrieve order details by order number",
    tags=["support_tools"]
)
def read_order_details(
    order_number: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieves order facts from the database."""
    details = get_order_details(db, order_number)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_number}' not found."
        )
    return details


@api_router.get(
    "/cases/{case_number}",
    summary="Retrieve case details by case number",
    tags=["support_tools"]
)
def read_case_details(
    case_number: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieves support case operational details."""
    details = get_case_details(db, case_number)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_number}' not found."
        )
    return details


@api_router.post(
    "/cases/{case_id}/tickets",
    status_code=status.HTTP_201_CREATED,
    summary="Create a real support ticket linked to a case",
    tags=["support_tools"]
)
def create_case_ticket(
    case_id: int,
    payload: CreateTicketRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Creates a support ticket persisted to the support_tickets table."""
    try:
        result = create_support_ticket(db, case_id=case_id, category=payload.category)
        return result
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@api_router.post(
    "/cases/{case_id}/events",
    status_code=status.HTTP_201_CREATED,
    summary="Record an audit event on a support case",
    tags=["support_tools"]
)
def record_event_for_case(
    case_id: int,
    payload: CreateEventRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Persists an audit event to the case_events table."""
    try:
        result = record_case_event(
            db,
            case_id=case_id,
            event_type=payload.event_type,
            message=payload.message,
            details_json=payload.details_json,
        )
        return result
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


# ---------------------------------------------------------------------------
# Level 4 & 5: LangGraph Multi-Agent Workflow Orchestration & Human Approval
# ---------------------------------------------------------------------------


def _build_workflow_resolve_response(final_state: Dict[str, Any], raw_complaint: str) -> WorkflowResolveResponse:
    """Helper to map a workflow state dictionary to the strongly typed WorkflowResolveResponse."""
    pe_obj = None
    if final_state.get("retrieved_policy_passages") is not None:
        pe_obj = PolicyRetrievalResult(
            query=raw_complaint,
            passages=[PolicyPassageSchema(**p) for p in final_state.get("retrieved_policy_passages", [])],
            found_relevant=not final_state.get("insufficient_evidence", False) and len(final_state.get("retrieved_policy_passages", [])) > 0,
            retrieval_method=final_state.get("retrieval_method") or "semantic_search",
            explanation="Retrieved via workflow orchestration.",
            policy_ids=final_state.get("policy_ids", []),
            source_files=[m.get("doc", "") for m in final_state.get("policy_source_metadata", [])],
            conflict_status=final_state.get("policy_conflict_status"),
            needs_review=final_state.get("policy_conflict_status") == "needs_review",
            insufficient_evidence=final_state.get("insufficient_evidence", False),
        )

    status_str = final_state.get("workflow_status", "completed")
    needs_review_bool = final_state.get("needs_review", False) or (status_str == "needs_review")
    supervisor_approved = final_state.get("supervisor_approved", False) or final_state.get("supervisor_decision") == "approved"
    supervisor_rejected = status_str == "rejected" or final_state.get("supervisor_decision") == "rejected"

    if supervisor_rejected:
        status_str = "rejected"
        needs_review_bool = False
    elif supervisor_approved:
        needs_review_bool = False
    else:
        requires_approval_flag = (
            final_state.get("requires_supervisor_approval", False)
            or final_state.get("requires_human_approval", False)
            or (final_state.get("recommended_resolution") or {}).get("human_approval_required", False)
            or (final_state.get("recommended_resolution") or {}).get("requires_supervisor_approval", False)
        )
        if requires_approval_flag or status_str == "needs_review":
            needs_review_bool = True
            if status_str == "completed":
                status_str = "needs_review"

    return WorkflowResolveResponse(
        workflow_id=final_state["workflow_id"],
        thread_id=final_state.get("thread_id"),
        case_id=final_state.get("case_id"),
        case_number=final_state.get("case_number"),
        status=status_str,
        current_stage=final_state.get("current_stage", "finalized"),
        complaint_analysis=ComplaintAnalysisResult(**final_state["complaint_analysis"]) if final_state.get("complaint_analysis") else None,
        order_investigation=OrderInvestigationResult(**final_state["order_investigation"]) if final_state.get("order_investigation") else None,
        policy_evidence=pe_obj,
        retrieval_method=final_state.get("retrieval_method"),
        recommended_resolution=ResolutionRecommendationResult(**final_state["recommended_resolution"]) if final_state.get("recommended_resolution") else None,
        verification_result=VerificationResult(**final_state["verification_result"]) if final_state.get("verification_result") else None,
        needs_review=needs_review_bool,
        escalation_reason=final_state.get("escalation_reason"),
        supervisor_decision=final_state.get("supervisor_decision"),
        missing_information=final_state.get("missing_information", []),
        clarification_details=final_state.get("clarification_details"),
        errors=final_state.get("errors", []),
        retry_count=final_state.get("retry_count", 0),
        events_recorded=final_state.get("events_recorded", []),
        created_at=final_state.get("created_at", ""),
        updated_at=final_state.get("updated_at", ""),
    )


@api_router.post(
    "/workflows/resolve",
    response_model=WorkflowResolveResponse,
    status_code=status.HTTP_200_OK,
    summary="Autonomous multi-agent customer support resolution workflow",
    tags=["workflows"],
)
def resolve_workflow(payload: WorkflowResolveRequest) -> WorkflowResolveResponse:
    """
    Executes the multi-agent orchestration workflow.
    Coordinates complaint analysis, order investigation, semantic policy retrieval,
    resolution recommendation, independent verification, and conditional routing.
    If supervisor review is required, pauses at checkpoint with status 'needs_review'.
    """
    raw_complaint = (payload.complaint_text or "").strip()
    if not raw_complaint:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Complaint text must not be empty or whitespace.",
        )

    try:
        final_state = run_resolution_workflow(
            complaint_text=raw_complaint,
            order_number=payload.order_number,
            case_number=payload.case_number,
            case_id=payload.case_id,
            customer_id=payload.customer_id,
            category=payload.category,
            seller_id=payload.seller_id,
        )
    except Exception as e:
        logger.error("Workflow execution encountered error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during workflow execution.",
        )

    return _build_workflow_resolve_response(final_state, raw_complaint)


# ---------------------------------------------------------------------------
# Level 5: Human Supervisor Approval & Review Endpoints
# ---------------------------------------------------------------------------

@api_router.get(
    "/workflows/pending-approvals",
    response_model=PendingApprovalsResponse,
    status_code=status.HTTP_200_OK,
    summary="List cases awaiting human supervisor review",
    tags=["workflows", "approvals"],
)
def list_pending_approvals(
    limit: int = Query(20, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Page offset (>=0)"),
    db: Session = Depends(get_db),
) -> PendingApprovalsResponse:
    """Retrieves paginated list of approval requests currently pending supervisor decision."""
    result = get_pending_approval_requests(db, limit=limit, offset=offset)
    return PendingApprovalsResponse(**result)


@api_router.get(
    "/workflows/{thread_id}/approval",
    response_model=ApprovalDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details of a case pending supervisor approval",
    tags=["workflows", "approvals"],
)
def get_approval_details(
    thread_id: str,
    db: Session = Depends(get_db),
) -> ApprovalDetailResponse:
    """Retrieves full investigation facts and policy evidence for a specific approval request thread."""
    clean_thread = (thread_id or "").strip()
    record = get_approval_request_by_thread_id(db, clean_thread)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request for thread '{clean_thread}' not found.",
        )
    return ApprovalDetailResponse(**record)


# ---------------------------------------------------------------------------
# Level 6: Authentication & Current User Endpoints
# ---------------------------------------------------------------------------

@api_router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate supervisor or agent credentials and receive Bearer token",
    tags=["auth"],
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticates username and password against database.
    Returns signed HMAC-SHA256 Bearer token and user profile on success.
    """
    user = authenticate_user(db, username=payload.username, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(username=user.username, role=user.role, user_id=user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@api_router.get(
    "/auth/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile and assigned RBAC role",
    tags=["auth"],
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns currently authenticated user profile."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


# ---------------------------------------------------------------------------
# Level 5 & 6: Human Supervisor Approval & Review Endpoints (RBAC-Protected)
# ---------------------------------------------------------------------------

@api_router.post(
    "/workflows/{thread_id}/approve",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a pending resolution and resume workflow",
    tags=["workflows", "approvals"],
)
def approve_workflow_case(
    thread_id: str,
    payload: ApprovalDecisionRequest,
    reviewer: AuthenticatedReviewer = Depends(get_approval_reviewer),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    """
    Submits an authorized supervisor approval decision and resumes the saved workflow
    from its SQLite checkpoint to complete remaining steps.
    Enforces RBAC approval thresholds and production authentication boundary.
    """
    clean_thread = (thread_id or "").strip()

    # 1. Determine effective reviewer identity
    if not reviewer.is_dev_fallback and reviewer.user:
        reviewer_id = reviewer.reviewer_id
    else:
        reviewer_id = (payload.reviewer_id or "").strip()
        if not reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reviewer identity (reviewer_id) must not be empty.",
            )

    # 2. Check existing approval request
    existing = get_approval_request_by_thread_id(db, clean_thread)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request for thread '{clean_thread}' not found.",
        )
    if existing["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval request has already been decided with status '{existing['status']}'.",
        )

    # 3. RBAC threshold enforcement
    order_total = 0
    if existing.get("order") and existing["order"].get("total_amount"):
        order_total = existing["order"]["total_amount"]

    authorized, err_msg = is_role_authorized_for_approval(reviewer.role, order_total)
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=err_msg,
        )

    # 4. Level 6: SLA Expiration Protection & Override Enforcement
    approval_obj = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.thread_id == clean_thread)
    ).scalar_one_or_none()
    if approval_obj:
        allowed, sla_err = validate_approval_decision_sla(
            approval=approval_obj,
            reviewer_role=reviewer.role,
            override_expired=payload.override_expired,
        )
        if not allowed:
            if reviewer.role != ROLE_SENIOR_SUPERVISOR:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=sla_err)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sla_err)

    try:
        updated_record = record_approval_decision(
            db,
            thread_id=clean_thread,
            decision="approved",
            reviewer_id=reviewer_id,
            reason=payload.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error("Database error recording approval: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record decision.")

    # Record explicit override event if expired request was approved by senior supervisor
    if approval_obj and approval_obj.is_expired and payload.override_expired:
        try:
            record_case_event(
                db,
                case_id=approval_obj.case_id,
                event_type="expired_approval_override",
                message=f"Senior supervisor '{reviewer_id}' executed authorized approval override for expired request #{approval_obj.id}.",
                details_json=json.dumps({"reviewer_id": reviewer_id, "action": "approved", "reason": payload.reason}),
            )
        except Exception as e:
            logger.warning("Could not record expired approval override event: %s", e)

    # Resume workflow from checkpoint
    try:
        graph = get_resolution_graph()
        config = {"configurable": {"thread_id": clean_thread}}
        resume_cmd = Command(resume={"action": "approve", "reviewer_id": reviewer_id, "reason": payload.reason or ""})
        final_state = graph.invoke(resume_cmd, config=config)
    except Exception as e:
        logger.error("Error resuming workflow from checkpoint: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming workflow from checkpoint: {e}",
        )

    wf_resp = _build_workflow_resolve_response(final_state, final_state.get("customer_complaint", ""))

    return ApprovalDecisionResponse(
        id=updated_record["id"],
        case_id=updated_record["case_id"],
        thread_id=clean_thread,
        status="approved",
        workflow_status=wf_resp.status,
        reviewer_id=reviewer_id,
        decision_reason=payload.reason,
        decision_timestamp=updated_record["decision_timestamp"],
        is_expired_override=bool(approval_obj and approval_obj.is_expired and payload.override_expired),
        workflow_result=wf_resp,
    )


@api_router.post(
    "/workflows/{thread_id}/reject",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a pending resolution and terminate proposed action",
    tags=["workflows", "approvals"],
)
def reject_workflow_case(
    thread_id: str,
    payload: ApprovalDecisionRequest,
    reviewer: AuthenticatedReviewer = Depends(get_approval_reviewer),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    """
    Submits an authorized supervisor rejection decision with required reason,
    halting the workflow without executing any proposed actions.
    Enforces RBAC role permissions and production authentication boundary.
    """
    clean_thread = (thread_id or "").strip()

    # 1. Determine effective reviewer identity
    if not reviewer.is_dev_fallback and reviewer.user:
        reviewer_id = reviewer.reviewer_id
    else:
        reviewer_id = (payload.reviewer_id or "").strip()
        if not reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reviewer identity (reviewer_id) must not be empty.",
            )

    reason = (payload.reason or "").strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A non-empty rejection reason is required when rejecting a case.",
        )

    # 2. Check existing approval request
    existing = get_approval_request_by_thread_id(db, clean_thread)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request for thread '{clean_thread}' not found.",
        )
    if existing["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval request has already been decided with status '{existing['status']}'.",
        )

    # 3. RBAC role enforcement for rejection
    authorized, err_msg = is_role_authorized_for_rejection(reviewer.role)
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=err_msg,
        )

    # 4. Level 6: SLA Expiration Protection & Override Enforcement
    approval_obj = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.thread_id == clean_thread)
    ).scalar_one_or_none()
    if approval_obj:
        allowed, sla_err = validate_approval_decision_sla(
            approval=approval_obj,
            reviewer_role=reviewer.role,
            override_expired=payload.override_expired,
        )
        if not allowed:
            if reviewer.role != ROLE_SENIOR_SUPERVISOR:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=sla_err)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sla_err)

    try:
        updated_record = record_approval_decision(
            db,
            thread_id=clean_thread,
            decision="rejected",
            reviewer_id=reviewer_id,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error("Database error recording rejection: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record decision.")

    # Record explicit override event if expired request was rejected by senior supervisor
    if approval_obj and approval_obj.is_expired and payload.override_expired:
        try:
            record_case_event(
                db,
                case_id=approval_obj.case_id,
                event_type="expired_approval_override",
                message=f"Senior supervisor '{reviewer_id}' executed authorized rejection override for expired request #{approval_obj.id}.",
                details_json=json.dumps({"reviewer_id": reviewer_id, "action": "rejected", "reason": reason}),
            )
        except Exception as e:
            logger.warning("Could not record expired rejection override event: %s", e)

    # Resume workflow from checkpoint into rejection branch
    try:
        graph = get_resolution_graph()
        config = {"configurable": {"thread_id": clean_thread}}
        resume_cmd = Command(resume={"action": "reject", "reviewer_id": reviewer_id, "reason": reason})
        final_state = graph.invoke(resume_cmd, config=config)
    except Exception as e:
        logger.error("Error resuming workflow on rejection: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming workflow on rejection: {e}",
        )

    wf_resp = _build_workflow_resolve_response(final_state, final_state.get("customer_complaint", ""))

    return ApprovalDecisionResponse(
        id=updated_record["id"],
        case_id=updated_record["case_id"],
        thread_id=clean_thread,
        status="rejected",
        workflow_status=wf_resp.status,
        reviewer_id=reviewer_id,
        decision_reason=reason,
        decision_timestamp=updated_record["decision_timestamp"],
        is_expired_override=bool(approval_obj and approval_obj.is_expired and payload.override_expired),
        workflow_result=wf_resp,
    )


# ---------------------------------------------------------------------------
# Level 6 Phase 3: Customer Clarification Loop Endpoints
# ---------------------------------------------------------------------------

@api_router.post(
    "/workflows/{thread_id}/provide-information",
    response_model=ProvideInformationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit requested customer clarification to resume a paused workflow",
    tags=["workflows", "clarifications"],
)
def provide_workflow_information(
    thread_id: str,
    payload: ProvideInformationRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> ProvideInformationResponse:
    """
    Submits missing customer clarification (e.g. order number, defect details)
    and resumes the paused workflow from its LangGraph SQLite checkpoint.
    Re-evaluates order facts and policy evidence through independent agent verification.
    Enforces customer/thread ownership, prevents cross-customer order submissions,
    and safeguards approval/SLA invariants.
    """
    clean_thread = (thread_id or "").strip()
    if not clean_thread:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thread identifier (thread_id) must not be empty.",
        )

    # 1. Validate substantive payload content
    order_num = (payload.order_number or "").strip() or None
    details = (payload.additional_details or "").strip() or None
    category = (payload.category or "").strip() or None
    seller_id = (payload.seller_id or "").strip() or None

    if not any([order_num, details, category, seller_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one non-empty clarification field (order_number, additional_details, category, or seller_id) must be provided.",
        )

    # 2. Prevent filesystem path traversal and command injection
    if order_num:
        if any(seq in order_num for seq in ("..", "/", "\\")) or order_num.startswith(("/", "\\")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid order number format: filesystem paths or directory traversal patterns are prohibited.",
            )
    if details:
        if details.startswith(("/", "\\", "C:", "c:")) or "../" in details or "..\\" in details:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input: filesystem paths or directory traversal patterns are prohibited.",
            )

    # 3. Retrieve workflow state from LangGraph checkpoint store
    try:
        graph = get_resolution_graph()
        config = {"configurable": {"thread_id": clean_thread}}
        checkpoint_state = graph.get_state(config)
    except Exception as e:
        logger.error("Error accessing checkpointer for thread '%s': %s", clean_thread, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accessing workflow checkpoint: {e}",
        )

    if not checkpoint_state or not checkpoint_state.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow thread '{clean_thread}' not found.",
        )

    state_values = checkpoint_state.values
    wf_status = state_values.get("workflow_status")
    next_nodes = checkpoint_state.next or ()

    # 4. Verify thread is actively awaiting customer information
    if wf_status != "needs_information" or "customer_clarification" not in next_nodes:
        if wf_status == "needs_review":
            detail_msg = f"Workflow thread '{clean_thread}' is awaiting supervisor review, not customer information."
        elif wf_status == "completed":
            detail_msg = f"Workflow thread '{clean_thread}' has already completed. Duplicate submissions are prohibited."
        elif wf_status in ("rejected", "failed"):
            detail_msg = f"Workflow thread '{clean_thread}' is terminated with status '{wf_status}' and cannot receive information."
        else:
            detail_msg = f"Workflow thread '{clean_thread}' is not awaiting customer information (current status: '{wf_status}')."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail_msg)

    # 5. Security & Customer Ownership Enforcement
    # Identify customer owning the thread
    thread_customer_id = state_values.get("customer_id")
    case_id = state_values.get("case_id")
    if thread_customer_id is None and case_id:
        case_obj = db.execute(select(SupportCase).where(SupportCase.id == case_id)).scalar_one_or_none()
        if case_obj:
            thread_customer_id = case_obj.customer_id

    # Check caller authentication / customer identity
    caller_is_staff = current_user is not None
    verified_customer: Optional[Customer] = None

    if not caller_is_staff:
        # Customer direct request: customer credentials must be provided or verified
        cust_id = payload.customer_id
        cust_email = (payload.customer_email or "").strip() or None

        if cust_id:
            verified_customer = db.execute(select(Customer).where(Customer.id == cust_id)).scalar_one_or_none()
        elif cust_email:
            verified_customer = db.execute(select(Customer).where(Customer.email == cust_email)).scalar_one_or_none()

        # In production (or strict mode), require customer identification
        if settings.is_production or not settings.allow_dev_auth_fallback:
            if not verified_customer:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required: Provide a valid Bearer token or registered customer credentials (customer_id or customer_email).",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Thread ownership validation: If thread is linked to a customer, caller must match
        if verified_customer and thread_customer_id is not None:
            if verified_customer.id != thread_customer_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Customer identity does not match the owner of this workflow thread.",
                )

    # 6. Cross-Customer Order Submission Prevention
    # If an order_number is submitted, verify that it does not belong to another customer
    target_order: Optional[Order] = None
    if order_num:
        target_order = db.execute(select(Order).where(Order.order_number == order_num)).scalar_one_or_none()
        if target_order:
            # Check against thread customer
            if thread_customer_id is not None and target_order.customer_id != thread_customer_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Order '{order_num}' belongs to a different customer account. Cross-customer order submissions are prohibited.",
                )
            # Check against verified customer submitting
            if verified_customer is not None and target_order.customer_id != verified_customer.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Order '{order_num}' belongs to a different customer account. Cross-customer order submissions are prohibited.",
                )

    effective_customer_id = (
        verified_customer.id
        if verified_customer
        else (thread_customer_id or (target_order.customer_id if target_order else None))
    )

    # 7. Record Case Event in Database
    if case_id:
        try:
            record_case_event(
                db,
                case_id=case_id,
                event_type="customer_clarification_submitted",
                message=f"Customer submitted clarification for thread '{clean_thread}'.",
                details_json=json.dumps({
                    "order_number": order_num,
                    "has_additional_details": bool(details),
                    "category": category,
                    "customer_id": effective_customer_id,
                    "submitted_by": current_user.username if current_user else (verified_customer.email if verified_customer else "customer"),
                }),
            )
        except Exception as e:
            logger.warning("Could not persist customer clarification event for case %s: %s", case_id, e)

    # 8. Resume Workflow from Checkpoint
    resume_payload = {
        "order_number": order_num,
        "additional_details": details,
        "category": category,
        "seller_id": seller_id,
        "customer_id": effective_customer_id,
    }

    try:
        resume_cmd = Command(resume=resume_payload)
        final_state = graph.invoke(resume_cmd, config=config)
    except Exception as e:
        logger.error("Error resuming workflow from clarification checkpoint: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming workflow from checkpoint: {e}",
        )

    final_status = final_state.get("workflow_status", "in_progress")
    wf_resp = _build_workflow_resolve_response(final_state, final_state.get("customer_complaint", ""))

    # Formulate clear outcome message
    if final_status == "completed":
        out_status = "completed"
        msg = "Customer clarification verified; workflow completed successfully."
    elif final_status == "needs_review":
        out_status = "needs_review"
        msg = "Customer clarification verified; case requires supervisor review."
    elif final_status == "needs_information":
        out_status = "needs_information"
        msg = "Customer clarification received, but additional information is still required to proceed."
    else:
        out_status = "resumed"
        msg = f"Workflow processing resumed with status: {final_status}."

    return ProvideInformationResponse(
        thread_id=clean_thread,
        case_id=final_state.get("case_id"),
        status=out_status,
        workflow_status=wf_resp.status,
        message=msg,
        missing_information=final_state.get("missing_information", []),
        clarification_details=final_state.get("clarification_details"),
        workflow_result=wf_resp,
    )


# ---------------------------------------------------------------------------
# Level 6 Phase 4: Customer Clarification Queue Endpoints
# ---------------------------------------------------------------------------

@api_router.get(
    "/workflows/pending-clarifications",
    response_model=PendingClarificationsResponse,
    status_code=status.HTTP_200_OK,
    summary="List workflows awaiting customer clarification",
    tags=["workflows", "clarifications"],
)
def list_pending_clarifications(
    limit: int = Query(20, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Page offset (>=0)"),
    db: Session = Depends(get_db),
) -> PendingClarificationsResponse:
    """Retrieves paginated list of workflow threads currently paused awaiting customer information."""
    result = get_pending_clarifications(db, limit=limit, offset=offset)
    return PendingClarificationsResponse(**result)


@api_router.get(
    "/workflows/{thread_id}/clarification",
    response_model=ClarificationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details of a workflow thread awaiting customer clarification",
    tags=["workflows", "clarifications"],
)
def get_clarification_details(
    thread_id: str,
    db: Session = Depends(get_db),
) -> ClarificationDetailResponse:
    """Retrieves detailed state context, missing fields, and reasons for a workflow paused awaiting customer input."""
    clean_thread = (thread_id or "").strip()
    record = get_clarification_by_thread_id(db, clean_thread)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow thread '{clean_thread}' not found or is not currently awaiting customer clarification.",
        )
    return ClarificationDetailResponse(**record)


# ---------------------------------------------------------------------------
# Level 6 Phase 5: Customer Portal & Secure Ownership Endpoints
# ---------------------------------------------------------------------------

@api_router.post(
    "/customer/verify-access",
    response_model=CustomerAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Secure customer ownership verification and session creation",
    tags=["customer"],
)
def customer_verify_access(
    payload: CustomerVerifyAccessRequest,
    db: Session = Depends(get_db),
) -> CustomerAccessResponse:
    """
    Verifies that the caller owns the provided email and linked order or case.
    Issues a scoped customer session bearer token and returns authorized case summaries.
    Enforces authorization on backend, preventing unauthorized data exposure.
    """
    clean_email = (payload.email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Valid customer email address is required.",
        )

    customer = db.scalar(
        select(Customer).where(func.lower(Customer.email) == clean_email)
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered customer account found for '{clean_email}'. Please check your email.",
        )

    # If order_number is specified, verify ownership
    order_num = (payload.order_number or "").strip()
    if order_num:
        order = db.scalar(
            select(Order).where(
                Order.order_number == order_num,
                Order.customer_id == customer.id,
            )
        )
        if not order:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Order '{order_num}' is not associated with customer '{clean_email}'.",
            )

    # If case_number is specified, verify ownership
    case_num = (payload.case_number or "").strip()
    if case_num:
        case = db.scalar(
            select(SupportCase).where(
                SupportCase.case_number == case_num,
                SupportCase.customer_id == customer.id,
            )
        )
        if not case:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Support case '{case_num}' is not associated with customer '{clean_email}'.",
            )

    # Generate signed customer access token
    token = create_customer_token(customer_id=customer.id, email=customer.email)

    # Retrieve customer's support cases
    cases_records = db.scalars(
        select(SupportCase)
        .where(SupportCase.customer_id == customer.id)
        .order_by(SupportCase.created_at.desc())
    ).all()

    # Check pending clarifications to populate thread_id and clarification_needed
    pending_threads_map = {}
    try:
        pending_clarifs = get_pending_clarifications(db, limit=100)
        for item in pending_clarifs.get("items", []):
            if item.get("case_id"):
                pending_threads_map[item["case_id"]] = item.get("thread_id")
    except Exception:
        pass

    case_summaries = []
    for c in cases_records:
        ord_rec = db.scalar(select(Order).where(Order.id == c.order_id)) if c.order_id else None
        active_thread = pending_threads_map.get(c.id)
        case_summaries.append(
            CustomerCaseSummary(
                case_number=c.case_number,
                order_number=ord_rec.order_number if ord_rec else None,
                product_name=ord_rec.product_name if ord_rec else None,
                subject=c.subject,
                status=c.status,
                created_at=c.created_at,
                clarification_needed=bool(active_thread),
                thread_id=active_thread,
            )
        )

    return CustomerAccessResponse(
        access_token=token,
        token_type="bearer",
        customer_id=customer.id,
        customer_name=customer.name,
        customer_email=customer.email,
        cases=case_summaries,
    )


@api_router.get(
    "/customer/cases/{case_number}",
    response_model=CustomerCaseDetail,
    status_code=status.HTTP_200_OK,
    summary="Get sanitized support case detail for authenticated customer",
    tags=["customer"],
)
def get_customer_case_detail(
    case_number: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> CustomerCaseDetail:
    """
    Retrieves customer-safe case details.
    Enforces that customer token subject matches the case's customer_id.
    Omit internal supervisor notes and employee metadata.
    """
    clean_case = (case_number or "").strip()
    case_obj = db.scalar(
        select(SupportCase).where(SupportCase.case_number == clean_case)
    )
    if not case_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support case '{clean_case}' not found.",
        )

    # STRICT SECURITY CHECK: ownership enforcement
    if case_obj.customer_id != customer.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have authorization to view this support case.",
        )

    # Order details
    order_obj = db.scalar(select(Order).where(Order.id == case_obj.order_id)) if case_obj.order_id else None

    # Ticket details
    ticket_obj = db.scalar(
        select(SupportTicket)
        .where(SupportTicket.case_id == case_obj.id)
        .order_by(SupportTicket.created_at.desc())
    )

    # Check for active clarification
    clarif_needed = False
    active_thread = None
    clarif_prompt = None
    missing_fields = []

    try:
        pending_clarifs = get_pending_clarifications(db, limit=100)
        for item in pending_clarifs.get("items", []):
            if item.get("case_id") == case_obj.id or item.get("case_number") == case_obj.case_number:
                clarif_needed = True
                active_thread = item.get("thread_id")
                clarif_prompt = item.get("complaint_text")
                missing_fields = item.get("missing_information", [])
                break
    except Exception:
        pass

    return CustomerCaseDetail(
        case_number=case_obj.case_number,
        order_number=order_obj.order_number if order_obj else None,
        product_name=order_obj.product_name if order_obj else None,
        order_status=order_obj.order_status if order_obj else None,
        delivery_status=order_obj.delivery_status if order_obj else None,
        subject=case_obj.subject,
        complaint_text=case_obj.complaint_text,
        status=case_obj.status,
        priority=case_obj.priority,
        resolution_summary=case_obj.resolution_summary,
        ticket_number=ticket_obj.ticket_number if ticket_obj else None,
        created_at=case_obj.created_at,
        updated_at=case_obj.updated_at,
        clarification_needed=clarif_needed,
        thread_id=active_thread,
        clarification_prompt=clarif_prompt,
        missing_fields=missing_fields,
    )


@api_router.get(
    "/customer/cases",
    response_model=List[CustomerCaseSummary],
    status_code=status.HTTP_200_OK,
    summary="List all support cases for authenticated customer",
    tags=["customer"],
)
def list_customer_cases(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> List[CustomerCaseSummary]:
    """Retrieves all cases associated with authenticated customer account."""
    cases_records = db.scalars(
        select(SupportCase)
        .where(SupportCase.customer_id == customer.customer_id)
        .order_by(SupportCase.created_at.desc())
    ).all()

    pending_threads_map = {}
    try:
        pending_clarifs = get_pending_clarifications(db, limit=100)
        for item in pending_clarifs.get("items", []):
            if item.get("case_id"):
                pending_threads_map[item["case_id"]] = item.get("thread_id")
    except Exception:
        pass

    res = []
    for c in cases_records:
        ord_rec = db.scalar(select(Order).where(Order.id == c.order_id)) if c.order_id else None
        active_thread = pending_threads_map.get(c.id)
        res.append(
            CustomerCaseSummary(
                case_number=c.case_number,
                order_number=ord_rec.order_number if ord_rec else None,
                product_name=ord_rec.product_name if ord_rec else None,
                subject=c.subject,
                status=c.status,
                created_at=c.created_at,
                clarification_needed=bool(active_thread),
                thread_id=active_thread,
            )
        )
    return res


# ---------------------------------------------------------------------------
# Level 6 Phase 5: Read-Only Audit History & Analytics Endpoints (Staff RBAC)
# ---------------------------------------------------------------------------

@api_router.get(
    "/cases/{case_id}/events",
    response_model=CaseEventsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve read-only chronological audit history for a support case",
    tags=["cases", "audit"],
)
def read_case_events(
    case_id: int,
    limit: int = Query(50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Page offset (>=0)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseEventsListResponse:
    """
    Enforces staff authentication and returns chronological audit history.
    """
    case = db.scalar(select(SupportCase).where(SupportCase.id == case_id))
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support case with id={case_id} not found.",
        )
    events = get_case_events(db, case_id=case_id, limit=limit, offset=offset)
    return CaseEventsListResponse(
        case_id=case_id,
        events=[
            CaseEventResponse(
                id=e["id"],
                case_id=e["case_id"],
                event_type=e["event_type"],
                message=e["message"],
                details_json=e["details_json"],
                created_at=e["created_at"],
            )
            for e in events
        ],
    )


@api_router.get(
    "/cases/by-number/{case_number}/events",
    response_model=CaseEventsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve read-only chronological audit history by case number",
    tags=["cases", "audit"],
)
def read_case_events_by_number(
    case_number: str,
    limit: int = Query(50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Page offset (>=0)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseEventsListResponse:
    clean_case = (case_number or "").strip()
    case = db.scalar(select(SupportCase).where(SupportCase.case_number == clean_case))
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support case '{clean_case}' not found.",
        )
    events = get_case_events(db, case_id=case.id, limit=limit, offset=offset)
    return CaseEventsListResponse(
        case_id=case.id,
        events=[
            CaseEventResponse(
                id=e["id"],
                case_id=e["case_id"],
                event_type=e["event_type"],
                message=e["message"],
                details_json=e["details_json"],
                created_at=e["created_at"],
            )
            for e in events
        ],
    )


@api_router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve operational metrics and KPI overview for staff",
    tags=["analytics"],
)
def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """
    Returns aggregated operational metrics directly computed from real database records.
    Requires staff authentication.
    """
    stats = get_analytics_summary(db)
    return AnalyticsOverviewResponse(**stats)




