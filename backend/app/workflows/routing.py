"""
Conditional routing logic for ResolveAI Level 4 LangGraph Multi-Agent Workflow.
Encapsulates deterministic, rule-based branching decisions based on structured state values.
"""

from typing import Literal
from app.core.logging_config import logger
from app.workflows.state import WorkflowState


def route_after_init(state: WorkflowState) -> Literal["analyze_complaint", "finalize_response"]:
    """
    Decides whether to proceed to complaint analysis or terminate immediately
    if initial validation failed (e.g. empty complaint).
    """
    if state.get("workflow_status") == "failed":
        logger.info("Validation failed at init. Routing to finalize_response.")
        return "finalize_response"
    return "analyze_complaint"


def route_after_verification(
    state: WorkflowState,
) -> Literal[
    "attempt_recovery",
    "handle_missing_information",
    "escalate_case",
    "record_resolution",
]:
    """
    Evaluates verified state and routes along defined conditional paths:
    1. Missing Order -> handle_missing_information (cannot resolve non-existent order)
    2. Policy Conflict -> escalate_case (precedence conflict requires human review)
    3. Verification Failure -> attempt_recovery (if retry < max_retries) or escalate_case
    4. Insufficient Policy Evidence -> escalate_case
    5. Supervisor / Human Approval Required -> escalate_case
    6. Missing Information requested by recommender -> handle_missing_information
    7. Clean Valid Recommendation -> record_resolution
    """
    ver = state.get("verification_result") or {}
    rec = state.get("recommended_resolution") or {}
    oi = state.get("order_investigation") or {}

    # 1. Missing Order Branch (Order does not exist in database)
    if state.get("missing_order", False) or (oi and not oi.get("order_exists", True)):
        logger.info("Order does not exist in database. Routing to handle_missing_information.")
        return "handle_missing_information"

    # 2. Policy Conflict Branch (Precedence conflict must escalate to supervisor review immediately)
    if state.get("policy_conflict_status") == "needs_review":
        logger.info("Policy precedence conflict detected. Routing to escalate_case.")
        return "escalate_case"

    # 3. Verification Failure Branch
    if not ver.get("is_valid", True) or ver.get("verification_status") == "fail":
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 1)
        if retry_count < max_retries:
            logger.info("Verification failed. Routing to attempt_recovery (retry %s of %s)", retry_count + 1, max_retries)
            return "attempt_recovery"
        else:
            logger.info("Verification failed and retry limit reached (%s). Routing to escalate_case", max_retries)
            return "escalate_case"

    # 4. Insufficient Policy Evidence Branch (ANY case with insufficient policy evidence must escalate)
    if state.get("insufficient_evidence", False):
        logger.info("Insufficient policy evidence detected. Routing to escalate_case.")
        return "escalate_case"

    # 5. Human / Supervisor Approval Required Branch
    has_approval_required = (
        state.get("requires_supervisor_approval", False)
        or state.get("requires_human_approval", False)
        or rec.get("requires_supervisor_approval", False)
        or rec.get("human_approval_required", False)
        or rec.get("requires_human_approval", False)
        or rec.get("recommendation_type") in ("escalate_to_human", "insufficient_evidence")
    )
    if has_approval_required:
        logger.info("Supervisor/Human approval required. Routing to escalate_case.")
        return "escalate_case"

    # 6. Missing Information Branch (Recommender requested additional customer facts)
    if rec.get("recommendation_type") == "request_more_info":
        logger.info("Recommendation requested customer details. Routing to handle_missing_information.")
        return "handle_missing_information"

    # 7. Valid Verified Recommendation
    logger.info("Recommendation passed all checks. Routing to record_resolution.")
    return "record_resolution"


def route_after_supervisor_review(
    state: WorkflowState,
) -> Literal["record_resolution", "finalize_response"]:
    """
    Level 5: Evaluates the supervisor review decision and routes accordingly:
    1. If supervisor rejected the recommendation -> finalize_response immediately.
       record_resolution must NEVER be called on rejected resolutions.
    2. Safety Invariant Check:
       Even if supervisor approved, verify that policy conflicts, missing orders,
       insufficient evidence, or verification failures do NOT bypass the safety rules.
       If any violation is present, divert to finalize_response without completion.
    3. If approved and passes safety invariants -> record_resolution.
    """
    if (
        state.get("supervisor_decision") == "rejected"
        or state.get("workflow_status") == "rejected"
    ):
        logger.info("Supervisor rejected resolution. Routing to finalize_response.")
        return "finalize_response"

    # Safety invariant checks
    ver = state.get("verification_result") or {}
    ver_failed = not ver.get("is_valid", True) or ver.get("verification_status") == "fail"
    has_conflict = state.get("policy_conflict_status") == "needs_review"
    insufficient_ev = state.get("insufficient_evidence", False)
    oi = state.get("order_investigation") or {}
    missing_ord = state.get("missing_order", False) or (oi and not oi.get("order_exists", True))

    if has_conflict or insufficient_ev or ver_failed or missing_ord:
        logger.warning(
            "Supervisor approved, but case violates safety invariant (conflict=%s, "
            "insufficient_ev=%s, ver_failed=%s, missing_ord=%s). Routing to finalize_response.",
            has_conflict,
            insufficient_ev,
            ver_failed,
            missing_ord,
        )
        return "finalize_response"

    if state.get("supervisor_approved") or state.get("supervisor_decision") == "approved":
        logger.info("Supervisor approved resolution and safety checks passed. Routing to record_resolution.")
        return "record_resolution"

    return "finalize_response"


def route_after_customer_clarification(
    state: WorkflowState,
) -> Literal["investigate_order", "finalize_response"]:
    """
    Level 6 Phase 3: Evaluates workflow state after customer clarification is submitted.
    Routes to investigate_order to re-evaluate order facts and policy evidence.
    If fatal error occurred, routes to finalize_response.
    """
    if state.get("workflow_status") == "failed":
        logger.info("Clarification state marked failed. Routing to finalize_response.")
        return "finalize_response"
    logger.info("Resuming workflow from customer clarification. Routing to investigate_order.")
    return "investigate_order"


