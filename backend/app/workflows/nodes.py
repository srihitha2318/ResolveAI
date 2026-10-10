"""
Node implementations for ResolveAI Level 4 LangGraph Multi-Agent Workflow Orchestration.
Each node executes a distinct agent responsibility, updates strongly typed state,
and records database events via short-lived transactions.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import logger
from app.database.db import SessionLocal
from app.database.models import SupportCase, Order
from app.agents.complaint_analyzer import ComplaintAnalyzerAgent
from app.agents.order_investigator import OrderInvestigatorAgent
from app.agents.policy_retriever import PolicyRetrieverAgent
from app.agents.resolution_recommender import ResolutionRecommenderAgent
from app.agents.verifier import VerifierAgent
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
)
from langgraph.types import interrupt

from app.tools.support_tools import (
    create_support_ticket,
    record_case_event,
    update_case_status,
    create_or_update_approval_request,
)
from app.workflows.state import WorkflowState


def _record_event_helper(
    case_id: Optional[int],
    event_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Safely records a case event in the database if case_id exists.
    Always returns a serializable audit record dictionary.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "event_type": event_type,
        "message": message,
        "case_id": case_id,
        "created_at": now_iso,
        "details": details or {},
    }

    if case_id is not None and isinstance(case_id, int):
        try:
            with SessionLocal() as db:
                details_json = json.dumps(details) if details else None
                persisted = record_case_event(
                    db=db,
                    case_id=case_id,
                    event_type=event_type,
                    message=message,
                    details_json=details_json,
                )
                record["id"] = persisted.get("id")
        except Exception as e:
            logger.warning("Could not persist case event '%s' for case_id=%s: %s", event_type, case_id, e)

    return record


# ---------------------------------------------------------------------------
# Node 1: Initialize Case State
# ---------------------------------------------------------------------------

def initialize_case_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Validates input complaint text, links existing support cases if referenced,
    and initializes execution state.
    """
    complaint_raw = (state.get("customer_complaint") or "").strip()
    events = list(state.get("events_recorded", []))
    errors = list(state.get("errors", []))

    # Fast validation: reject empty or whitespace complaints
    if not complaint_raw:
        errors.append("Customer complaint text is empty or missing.")
        case_id = state.get("case_id")
        if case_id:
            evt = _record_event_helper(
                case_id=case_id,
                event_type="workflow_failed",
                message="Workflow failed: Customer complaint text is empty or missing.",
                details={"error": "empty_complaint"},
            )
            events.append(evt)
        return {
            "workflow_status": "failed",
            "current_stage": "initialize_case",
            "errors": errors,
            "missing_information": ["customer_complaint"],
            "events_recorded": events,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    case_id = state.get("case_id")
    case_number = state.get("case_number")
    order_id = state.get("order_id")
    order_number = state.get("order_number")
    customer_id = state.get("customer_id")

    # If case_id or case_number is provided, inspect database to enrich context
    if (case_id or case_number) and (order_number is None or customer_id is None):
        try:
            with SessionLocal() as db:
                stmt = select(SupportCase)
                if case_id:
                    stmt = stmt.where(SupportCase.id == case_id)
                elif case_number:
                    stmt = stmt.where(SupportCase.case_number == case_number)

                case_obj = db.execute(stmt).scalar_one_or_none()
                if case_obj:
                    case_id = case_obj.id
                    case_number = case_obj.case_number
                    customer_id = customer_id or case_obj.customer_id
                    order_id = order_id or case_obj.order_id
                    if order_id and not order_number:
                        ord_obj = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
                        if ord_obj:
                            order_number = ord_obj.order_number
        except Exception as e:
            logger.warning("Error looking up existing case during initialization: %s", e)
            errors.append(f"Database lookup error during case initialization: {e}")

    evt = _record_event_helper(
        case_id=case_id,
        event_type="workflow_started",
        message=f"Autonomous workflow '{state.get('workflow_id')}' started.",
    )
    events.append(evt)

    return {
        "case_id": case_id,
        "case_number": case_number,
        "order_id": order_id,
        "order_number": order_number,
        "customer_id": customer_id,
        "current_stage": "initialize_case",
        "workflow_status": "in_progress",
        "events_recorded": events,
        "errors": errors,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 2: Analyze Customer Complaint
# ---------------------------------------------------------------------------

def analyze_complaint_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Executes complaint analysis using ComplaintAnalyzerAgent.
    Extracts category, main issue, desired outcome, and referenced order number.
    """
    if state.get("workflow_status") == "failed":
        return {}

    analyzer = ComplaintAnalyzerAgent()
    input_data = ComplaintAnalysisInput(
        complaint_text=state.get("customer_complaint", ""),
        order_number=state.get("order_number"),
        case_id=state.get("case_id"),
    )

    result: ComplaintAnalysisResult = analyzer.analyze(input_data)
    result_dict = result.model_dump()

    # If order_number was not provided in state but analyzer extracted one from text, adopt it
    adopted_order = state.get("order_number") or result.order_number

    events = list(state.get("events_recorded", []))
    evt = _record_event_helper(
        case_id=state.get("case_id"),
        event_type="complaint_analyzed",
        message=f"Complaint classified as '{result.category}': {result.main_issue}",
        details={"category": result.category, "order_number": adopted_order},
    )
    events.append(evt)

    return {
        "complaint_analysis": result_dict,
        "complaint_category": result.category,
        "order_number": adopted_order,
        "current_stage": "analyze_complaint",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 3: Investigate Order
# ---------------------------------------------------------------------------

def investigate_order_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Executes order investigation using OrderInvestigatorAgent with real database session.
    Retrieves facts, delivery status, customer history, and seller/category metadata.
    """
    if state.get("workflow_status") == "failed":
        return {}

    investigator = OrderInvestigatorAgent()
    input_data = OrderInvestigationInput(
        order_number=state.get("order_number"),
        case_number=state.get("case_number"),
    )

    with SessionLocal() as db:
        result: OrderInvestigationResult = investigator.investigate(db=db, input_data=input_data)

    result_dict = result.model_dump()

    category = state.get("category")
    seller_id = state.get("seller_id")
    order_id = state.get("order_id")
    customer_id = state.get("customer_id")
    order_status = None

    if result.order_exists and result.order_details:
        od = result.order_details
        order_id = order_id or od.id
        customer_id = customer_id or od.customer_id
        category = category or od.category
        seller_id = seller_id or od.seller_id
        order_status = od.order_status

    events = list(state.get("events_recorded", []))
    evt = _record_event_helper(
        case_id=state.get("case_id"),
        event_type="order_investigation_completed",
        message=f"Order investigation completed: exists={result.order_exists}, status={order_status}",
        details={"order_exists": result.order_exists, "order_number": state.get("order_number")},
    )
    events.append(evt)

    missing = list(state.get("missing_information", []))
    missing_order = not result.order_exists
    if not result.order_exists:
        missing.extend(result.missing_information)

    return {
        "order_investigation": result_dict,
        "order_id": order_id,
        "customer_id": customer_id,
        "category": category,
        "seller_id": seller_id,
        "order_status": order_status,
        "missing_order": missing_order,
        "missing_information": list(set(missing)),
        "current_stage": "investigate_order",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 4: Retrieve Relevant Policies
# ---------------------------------------------------------------------------

def retrieve_policy_evidence_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Retrieves authoritative policy evidence using PolicyRetrieverAgent (Level 3 Semantic RAG).
    Applies category and seller metadata filtering with automatic keyword fallback.
    """
    if state.get("workflow_status") == "failed":
        return {}

    retriever = PolicyRetrieverAgent()

    # Query formulation from main issue or raw complaint
    ca = state.get("complaint_analysis") or {}
    query_text = ca.get("main_issue") or state.get("customer_complaint") or "return refund policy"

    input_data = PolicySearchInput(
        query=query_text,
        seller_id=state.get("seller_id"),
        category=state.get("category"),
    )

    result: PolicyRetrievalResult = retriever.retrieve(input_data)
    result_dict = result.model_dump()

    events = list(state.get("events_recorded", []))
    evt = _record_event_helper(
        case_id=state.get("case_id"),
        event_type="policy_evidence_retrieved",
        message=(
            f"Policy retrieval via {result.retrieval_method}: found={result.found_relevant}, "
            f"policies={result.policy_ids}, conflict={result.conflict_status}"
        ),
        details={
            "retrieval_method": result.retrieval_method,
            "policy_ids": result.policy_ids,
            "found_relevant": result.found_relevant,
        },
    )
    events.append(evt)

    return {
        "retrieved_policy_passages": [p.model_dump() for p in result.passages],
        "policy_source_metadata": [{"doc": p.document_name, "id": p.policy_id, "scope": p.scope} for p in result.passages],
        "policy_ids": result.policy_ids,
        "retrieval_method": result.retrieval_method,
        "policy_conflict_status": result.conflict_status,
        "insufficient_evidence": result.insufficient_evidence or (not result.found_relevant),
        "current_stage": "retrieve_policy_evidence",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 5: Recommend Resolution
# ---------------------------------------------------------------------------

def recommend_resolution_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Synthesizes facts, order details, and policy evidence into an actionable recommendation.
    Enforces strict separation between proposing recommendations and executing actions.
    """
    if state.get("workflow_status") == "failed":
        return {}

    recommender = ResolutionRecommenderAgent()

    # Reconstruct typed Pydantic models from serialized state
    ca_obj = ComplaintAnalysisResult(**state["complaint_analysis"])
    oi_obj = OrderInvestigationResult(**state["order_investigation"])

    # Reconstruct PolicyRetrievalResult
    pe_data = {
        "query": state.get("customer_complaint", ""),
        "passages": state.get("retrieved_policy_passages", []),
        "found_relevant": not state.get("insufficient_evidence", False) and len(state.get("retrieved_policy_passages", [])) > 0,
        "retrieval_method": state.get("retrieval_method") or "semantic_search",
        "explanation": "Retrieved from workflow state.",
        "policy_ids": state.get("policy_ids", []),
        "source_files": [m.get("doc", "") for m in state.get("policy_source_metadata", [])],
        "conflict_status": state.get("policy_conflict_status"),
        "needs_review": state.get("policy_conflict_status") == "needs_review",
        "insufficient_evidence": state.get("insufficient_evidence", False),
    }
    pe_obj = PolicyRetrievalResult(**pe_data)

    rec_input = ResolutionRecommendationInput(
        complaint_analysis=ca_obj,
        order_investigation=oi_obj,
        policy_evidence=pe_obj,
    )

    result: ResolutionRecommendationResult = recommender.recommend(rec_input)
    result_dict = result.model_dump()
    result_dict["requires_supervisor_approval"] = result.human_approval_required

    events = list(state.get("events_recorded", []))
    evt = _record_event_helper(
        case_id=state.get("case_id"),
        event_type="resolution_recommended",
        message=f"Recommendation generated: '{result.title}' (type={result.recommendation_type})",
        details={"type": result.recommendation_type, "requires_approval": result.human_approval_required},
    )
    events.append(evt)

    return {
        "recommended_resolution": result_dict,
        "requires_human_approval": result.human_approval_required,
        "requires_supervisor_approval": result.human_approval_required,
        "current_stage": "recommend_resolution",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 6: Verify Resolution
# ---------------------------------------------------------------------------

def verify_resolution_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Executes independent factual consistency, order contradiction, and anti-hallucination verification.
    Ensures unverified resolutions are never accepted without validation.
    """
    if state.get("workflow_status") == "failed":
        return {}

    verifier = VerifierAgent()

    rec_obj = ResolutionRecommendationResult(**state["recommended_resolution"])
    oi_obj = OrderInvestigationResult(**state["order_investigation"]) if state.get("order_investigation") else None
    ca_obj = ComplaintAnalysisResult(**state["complaint_analysis"]) if state.get("complaint_analysis") else None

    pe_data = {
        "query": state.get("customer_complaint", ""),
        "passages": state.get("retrieved_policy_passages", []),
        "found_relevant": not state.get("insufficient_evidence", False) and len(state.get("retrieved_policy_passages", [])) > 0,
        "retrieval_method": state.get("retrieval_method") or "semantic_search",
        "explanation": "Verified from workflow state.",
        "policy_ids": state.get("policy_ids", []),
        "source_files": [m.get("doc", "") for m in state.get("policy_source_metadata", [])],
        "conflict_status": state.get("policy_conflict_status"),
        "needs_review": state.get("policy_conflict_status") == "needs_review",
        "insufficient_evidence": state.get("insufficient_evidence", False),
    }
    pe_obj = PolicyRetrievalResult(**pe_data)

    ver_input = VerificationInput(
        recommendation=rec_obj,
        complaint_analysis=ca_obj,
        order_investigation=oi_obj,
        policy_evidence=pe_obj,
    )

    result: VerificationResult = verifier.verify(ver_input)
    result_dict = result.model_dump()

    events = list(state.get("events_recorded", []))
    event_type = "resolution_verification_passed" if result.is_valid else "resolution_verification_failed"
    evt = _record_event_helper(
        case_id=state.get("case_id"),
        event_type=event_type,
        message=f"Verification result: status={result.verification_status}, valid={result.is_valid}",
        details={"issues": result.detected_issues},
    )
    events.append(evt)

    return {
        "verification_result": result_dict,
        "current_stage": "verify_resolution",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 7: Handle Missing Information & Clarification Loop
# ---------------------------------------------------------------------------

def _generate_clarification_details(missing_fields: List[str], state: WorkflowState) -> Dict[str, str]:
    """
    Generates structured, case-specific explanations for each missing field,
    detailing why it is strictly necessary to resolve the case.
    """
    reasons_map = {
        "order": "A valid order identifier (e.g. ORD-2026-001) is required to look up order records, shipping logs, and seller metadata.",
        "customer": "Customer account identification is required to verify ownership of the support case and order.",
        "photograph": "Visual photographic or video evidence of the defect is required to assess replacement eligibility under damage policy.",
        "unboxing": "Unboxing documentation is required to authenticate high-value electronics and prevent transit disputes.",
        "details": "Specific complaint context and details are required to accurately evaluate policy remedies.",
    }
    details: Dict[str, str] = {}
    for field in missing_fields:
        f_clean = field.strip()
        f_lower = f_clean.lower()
        matched = False
        for key, exp in reasons_map.items():
            if key in f_lower:
                details[f_clean] = exp
                matched = True
                break
        if not matched:
            details[f_clean] = f"Additional information for '{f_clean}' is required to process your request."
    return details


def handle_missing_information_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Routes cases with missing required facts (e.g. unknown order, missing photos)
    to a structured needs_information state with detailed explanations.
    """
    events = list(state.get("events_recorded", []))
    missing = list(state.get("missing_information", []))

    rec = state.get("recommended_resolution") or {}
    if rec.get("missing_information"):
        missing.extend(rec["missing_information"])

    missing = list(set([m for m in missing if m]))
    if not missing:
        missing = ["additional_order_details"]

    clarification_details = _generate_clarification_details(missing, state)

    evt = _record_event_helper(
        case_id=state.get("case_id"),
        event_type="case_needs_information",
        message=f"Workflow paused: missing information required from customer: {', '.join(missing)}",
        details={
            "missing_fields": missing,
            "clarification_details": clarification_details,
        },
    )
    events.append(evt)

    return {
        "workflow_status": "needs_information",
        "missing_information": missing,
        "clarification_details": clarification_details,
        "current_stage": "handle_missing_information",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 7b: Customer Clarification (Level 6 Phase 3 Interruption Point)
# ---------------------------------------------------------------------------

def customer_clarification_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Level 6 Phase 3: LangGraph interruption and checkpoint point for Customer Clarification Loops.
    Pauses execution while awaiting missing customer information (e.g. order number, defect photo, details).
    Persists workflow state under thread_id.
    Resumes when customer (or authorized frontline agent) submits clarification.
    """
    thread_id = state.get("thread_id")
    case_id = state.get("case_id")
    events = list(state.get("events_recorded", []))
    missing = list(state.get("missing_information", []))
    clarification_details = state.get("clarification_details") or {}

    # Interrupt execution and wait for customer information
    clarification_input = interrupt({
        "thread_id": thread_id,
        "case_id": case_id,
        "case_number": state.get("case_number"),
        "customer_id": state.get("customer_id"),
        "missing_information": missing,
        "clarification_details": clarification_details,
        "reason": "Missing required information from customer to proceed with case resolution.",
        "order_number": state.get("order_number"),
        "customer_complaint": state.get("customer_complaint"),
    })

    # Resumed from interrupt with customer payload
    if not isinstance(clarification_input, dict):
        clarification_input = {"additional_details": str(clarification_input)}

    new_order = clarification_input.get("order_number")
    additional_details = clarification_input.get("additional_details")
    new_cat = clarification_input.get("category")
    new_seller = clarification_input.get("seller_id")
    new_customer = clarification_input.get("customer_id")

    # Record workflow audit event
    evt = _record_event_helper(
        case_id=case_id,
        event_type="customer_information_submitted",
        message=f"Customer submitted clarification for thread '{thread_id}'.",
        details={
            "submitted_fields": [k for k, v in clarification_input.items() if v is not None],
            "order_number": new_order,
            "has_additional_details": bool(additional_details),
        },
    )
    events.append(evt)

    # Merge customer information into workflow state
    updated_complaint = state.get("customer_complaint", "")
    if additional_details and str(additional_details).strip():
        updated_complaint = f"{updated_complaint}\n[Customer Clarification]: {str(additional_details).strip()}"

    clarification_count = state.get("clarification_count", 0) + 1

    res_dict: Dict[str, Any] = {
        "workflow_status": "in_progress",
        "current_stage": "customer_clarification",
        "missing_order": False,
        "missing_information": [],
        "clarification_count": clarification_count,
        "customer_complaint": updated_complaint,
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if new_order and str(new_order).strip():
        res_dict["order_number"] = str(new_order).strip()
    if new_cat and str(new_cat).strip():
        res_dict["category"] = str(new_cat).strip()
    if new_seller and str(new_seller).strip():
        res_dict["seller_id"] = str(new_seller).strip()
    if new_customer:
        res_dict["customer_id"] = new_customer

    return res_dict


# ---------------------------------------------------------------------------
# Node 8: Escalate Case for Review
# ---------------------------------------------------------------------------

def escalate_case_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Safely routes complex, high-value, conflicting, or unverified cases
    to a human supervisor review queue without committing unauthorized actions.
    """
    events = list(state.get("events_recorded", []))
    case_id = state.get("case_id")

    # Determine primary reason for escalation
    ver = state.get("verification_result") or {}
    rec = state.get("recommended_resolution") or {}
    reason = state.get("escalation_reason")

    if not reason:
        if state.get("policy_conflict_status") == "needs_review":
            reason = f"Unresolved policy conflict among cited policies: {', '.join(state.get('policy_ids', []))}."
        elif state.get("insufficient_evidence"):
            reason = "No authoritative policy passage met semantic relevance threshold."
        elif not ver.get("is_valid", True):
            reason = f"Verification failure: {'; '.join(ver.get('detected_issues', ['Discrepancy detected']))}."
        elif (
            state.get("requires_supervisor_approval")
            or state.get("requires_human_approval")
            or rec.get("human_approval_required")
            or rec.get("requires_supervisor_approval")
        ):
            reason = f"High-value order or sensitive resolution requires supervisor sign-off ({rec.get('title')})."
        else:
            reason = "Case flagged for human supervisor review."

    thread_id = state.get("thread_id")
    case_number = state.get("case_number")
    customer_id = state.get("customer_id")
    order_id = state.get("order_id")

    # Ensure case_id exists in database for relational persistence
    if not case_id:
        try:
            with SessionLocal() as db:
                c_num = case_number or f"CASE-2026-{uuid.uuid4().hex[:6].upper()}"
                cust_id = customer_id or 1
                new_case = SupportCase(
                    case_number=c_num,
                    customer_id=cust_id,
                    order_id=order_id,
                    subject=f"Escalated Case: {state.get('order_number') or 'Support'}",
                    complaint_text=state.get("customer_complaint", "Customer complaint requiring supervisor review."),
                    status="escalated",
                    priority="high",
                )
                db.add(new_case)
                db.commit()
                db.refresh(new_case)
                case_id = new_case.id
                case_number = new_case.case_number
        except Exception as e:
            logger.warning("Could not auto-create SupportCase for escalation: %s", e)
    else:
        try:
            with SessionLocal() as db:
                update_case_status(db, case_id=case_id, new_status="escalated")
        except Exception as e:
            logger.warning("Could not update case status to 'escalated' for case_id=%s: %s", case_id, e)

    # Persist or update ApprovalRequest record
    if case_id:
        try:
            with SessionLocal() as db:
                create_or_update_approval_request(
                    db=db,
                    case_id=case_id,
                    thread_id=thread_id,
                    requested_action=rec.get("recommendation_type", "supervisor_review"),
                    justification=reason,
                    proposed_resolution=json.dumps(rec) if rec else None,
                    policy_evidence=json.dumps(state.get("retrieved_policy_passages", [])),
                )
        except Exception as e:
            logger.warning("Could not persist approval request for case_id=%s: %s", case_id, e)

    evt = _record_event_helper(
        case_id=case_id,
        event_type="case_needs_review",
        message=f"Case escalated to supervisor queue: {reason}",
        details={"reason": reason, "thread_id": thread_id},
    )
    events.append(evt)

    evt_req = _record_event_helper(
        case_id=case_id,
        event_type="approval_requested",
        message=f"Supervisor approval requested for thread '{thread_id}'.",
        details={"thread_id": thread_id, "reason": reason},
    )
    events.append(evt_req)

    return {
        "case_id": case_id,
        "case_number": case_number,
        "workflow_status": "needs_review",
        "needs_review": True,
        "requires_human_approval": True,
        "requires_supervisor_approval": True,
        "escalation_reason": reason,
        "current_stage": "escalate_case",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 8b: Human Supervisor Review (Level 5 Interruption Point)
# ---------------------------------------------------------------------------

def supervisor_review_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Level 5: Human-in-the-loop interruption point for supervisor review.
    Pauses workflow execution before recording resolution or committing business decisions.
    Persists state into the checkpoint database under thread_id.
    Resumes when an authorized supervisor submits an explicit approval or rejection decision.
    """
    thread_id = state.get("thread_id")
    case_id = state.get("case_id")
    events = list(state.get("events_recorded", []))

    # Interrupt execution and wait for human decision
    human_input = interrupt({
        "case_id": case_id,
        "case_number": state.get("case_number"),
        "thread_id": thread_id,
        "order_number": state.get("order_number"),
        "escalation_reason": state.get("escalation_reason"),
        "proposed_resolution": state.get("recommended_resolution"),
        "policy_evidence": state.get("retrieved_policy_passages"),
        "customer_complaint": state.get("customer_complaint"),
    })

    # Resumed from interrupt with decision payload
    if not isinstance(human_input, dict):
        human_input = {"action": str(human_input)}

    action = (human_input.get("action") or human_input.get("decision") or "").strip().lower()
    reviewer_id = (human_input.get("reviewer_id") or "supervisor").strip()
    reason = (human_input.get("reason") or "").strip()

    # Record workflow_resumed audit event
    evt_resumed = _record_event_helper(
        case_id=case_id,
        event_type="workflow_resumed",
        message=f"Workflow resumed from checkpoint by supervisor '{reviewer_id}' with action '{action}'.",
        details={"reviewer_id": reviewer_id, "action": action, "reason": reason},
    )
    events.append(evt_resumed)

    if action in ("approve", "approved"):
        evt_decision = _record_event_helper(
            case_id=case_id,
            event_type="approval_granted",
            message=f"Supervisor '{reviewer_id}' approved resolution" + (f": {reason}" if reason else "."),
            details={"reviewer_id": reviewer_id, "reason": reason, "action": "approve"},
        )
        events.append(evt_decision)

        return {
            "supervisor_decision": "approved",
            "supervisor_reviewer": reviewer_id,
            "supervisor_reason": reason,
            "supervisor_approved": True,
            "requires_supervisor_approval": False,
            "requires_human_approval": False,
            "workflow_status": "in_progress",
            "current_stage": "supervisor_review",
            "events_recorded": events,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        evt_decision = _record_event_helper(
            case_id=case_id,
            event_type="approval_rejected",
            message=f"Supervisor '{reviewer_id}' rejected resolution: {reason}",
            details={"reviewer_id": reviewer_id, "reason": reason, "action": "reject"},
        )
        events.append(evt_decision)

        return {
            "supervisor_decision": "rejected",
            "supervisor_reviewer": reviewer_id,
            "supervisor_reason": reason,
            "supervisor_approved": False,
            "requires_supervisor_approval": False,
            "requires_human_approval": False,
            "workflow_status": "rejected",
            "needs_review": False,
            "current_stage": "supervisor_review",
            "events_recorded": events,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }



# ---------------------------------------------------------------------------
# Node 9: Bounded Recovery Attempt
# ---------------------------------------------------------------------------

def attempt_recovery_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Performs bounded recovery on verification failure.
    Adjusts the recommendation to remove unverified claims or false completion statements,
    then loops back to verify_resolution with incremented retry count.
    """
    current_retries = state.get("retry_count", 0) + 1
    events = list(state.get("events_recorded", []))
    rec = dict(state.get("recommended_resolution") or {})
    ver = state.get("verification_result") or {}

    # Conservative recovery: sanitize recommendation reasoning and action
    issues = ver.get("detected_issues", [])
    logger.info("Attempting bounded recovery (retry #%s) for issues: %s", current_retries, issues)

    # Sanitize title and action to remove completion claims
    rec["title"] = f"Review & Evaluate: {rec.get('title', 'Resolution')}"
    rec["reasoning"] = (
        f"Under review. Discrepancy noted in initial evaluation: {'; '.join(issues)}. "
        f"Proceeding with conservative review recommendation."
    )
    rec["action_required"] = "Submit case details for manual supervisor evaluation without automated completion."
    rec["human_approval_required"] = True

    evt = _record_event_helper(
        case_id=state.get("case_id"),
        event_type="workflow_recovery_attempted",
        message=f"Recovery attempt #{current_retries}: sanitized recommendation to eliminate completion claims.",
        details={"retry_count": current_retries, "addressed_issues": issues},
    )
    events.append(evt)

    return {
        "retry_count": current_retries,
        "recommended_resolution": rec,
        "requires_human_approval": True,
        "current_stage": "attempt_recovery",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 10: Record Resolution & Create Ticket
# ---------------------------------------------------------------------------

def record_resolution_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Records verified resolution completion and creates a support ticket if appropriate.
    Marks workflow_status as 'completed'.
    """
    # Safety invariant check:
    # A case requiring supervisor approval, having a conflict, lacking evidence, with a missing order,
    # or failing verification MUST NEVER be marked as completed!
    supervisor_approved = state.get("supervisor_approved", False) or state.get("supervisor_decision") == "approved"
    requires_approval = (
        not supervisor_approved
        and (
            state.get("requires_supervisor_approval", False)
            or state.get("requires_human_approval", False)
            or (state.get("recommended_resolution") or {}).get("human_approval_required", False)
            or (state.get("recommended_resolution") or {}).get("requires_supervisor_approval", False)
        )
    )
    has_conflict = state.get("policy_conflict_status") == "needs_review"
    insufficient_ev = state.get("insufficient_evidence", False)
    ver = state.get("verification_result") or {}
    ver_failed = not ver.get("is_valid", True) or ver.get("verification_status") == "fail"
    missing_ord = state.get("missing_order", False) or (state.get("order_investigation") and not state.get("order_investigation", {}).get("order_exists", True))

    if requires_approval or has_conflict or insufficient_ev or ver_failed:
        logger.warning("record_resolution_node called but case requires review/escalation. Diverting to escalate_case.")
        return escalate_case_node(state)

    if missing_ord:
        logger.warning("record_resolution_node called but order is missing. Diverting to handle_missing_information.")
        return handle_missing_information_node(state)

    events = list(state.get("events_recorded", []))
    case_id = state.get("case_id")
    category = state.get("complaint_category") or "general"

    # Create tracking ticket if case exists
    if case_id:
        try:
            with SessionLocal() as db:
                ticket_info = create_support_ticket(db, case_id=case_id, category=category)
                events.append(_record_event_helper(
                    case_id=case_id,
                    event_type="ticket_created",
                    message=f"Support ticket {ticket_info.get('ticket_number')} created for category '{category}'",
                    details=ticket_info,
                ))
        except Exception as e:
            logger.warning("Could not auto-create ticket for case_id=%s: %s", case_id, e)

    evt = _record_event_helper(
        case_id=case_id,
        event_type="workflow_completed",
        message="Workflow completed successfully with verified resolution.",
    )
    events.append(evt)

    return {
        "workflow_status": "completed",
        "needs_review": False,
        "current_stage": "record_resolution",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Node 11: Finalize Response
# ---------------------------------------------------------------------------

def finalize_response_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Terminal node: finalizes timestamp, enforces safety invariants, and wraps execution result.
    """
    status = state.get("workflow_status", "completed")
    needs_review = state.get("needs_review", False)
    supervisor_approved = state.get("supervisor_approved", False) or state.get("supervisor_decision") == "approved"
    requires_approval = (
        not supervisor_approved
        and (
            state.get("requires_supervisor_approval", False)
            or state.get("requires_human_approval", False)
            or (state.get("recommended_resolution") or {}).get("human_approval_required", False)
            or (state.get("recommended_resolution") or {}).get("requires_supervisor_approval", False)
        )
    )

    events = list(state.get("events_recorded", []))

    # Invariant enforcement: Approval-required or needs_review cases can NEVER report as completed
    is_rejected = status == "rejected" or state.get("supervisor_decision") == "rejected"
    if is_rejected:
        status = "rejected"
        needs_review = False
    elif requires_approval or status == "needs_review":
        needs_review = True
        if status == "completed":
            status = "needs_review"


    # If workflow failed at init and no workflow_failed event was recorded yet
    if status == "failed" and not any(e.get("event_type") == "workflow_failed" for e in events):
        case_id = state.get("case_id")
        if case_id:
            evt = _record_event_helper(
                case_id=case_id,
                event_type="workflow_failed",
                message=f"Workflow failed: {'; '.join(state.get('errors', ['Validation error']))}",
                details={"errors": state.get("errors", [])},
            )
            events.append(evt)

    return {
        "workflow_status": status,
        "needs_review": needs_review,
        "current_stage": "finalized",
        "events_recorded": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
