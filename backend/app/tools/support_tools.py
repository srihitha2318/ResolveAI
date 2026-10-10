from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import logger
from app.core.policy_rules import (
    CURRENCY_CODE,
    CURRENCY_SYMBOL,
    TIER_1_MAX_AMOUNT_PAISE,
    HIGH_VALUE_THRESHOLD_PAISE,
    DEFAULT_RETURN_WINDOW_DAYS,
    CATEGORY_RETURN_WINDOWS,
    format_inr,
)
from app.database.models import (
    Customer,
    Order,
    SupportCase,
    SupportTicket,
    CaseEvent,
    ApprovalRequest,
    utc_now,
)
from app.core.sla import (
    calculate_sla_parameters,
    evaluate_pending_approvals_slas,
    evaluate_and_record_sla_breach,
)

# Allowed support case statuses
ALLOWED_CASE_STATUSES = {"open", "in_progress", "resolved", "closed", "escalated"}


def get_order_details(db: Session, order_number: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves stored order details without leaking unnecessary customer information.
    Returns None if the order does not exist. All monetary values are in integer paise (INR).
    """
    if not order_number or not isinstance(order_number, str):
        return None

    order = db.execute(
        select(Order).where(Order.order_number == order_number.strip())
    ).scalar_one_or_none()

    if not order:
        return None

    return {
        "id": order.id,
        "order_number": order.order_number,
        "product_name": order.product_name,
        "order_status": order.order_status,
        "delivery_status": order.delivery_status,
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "expected_delivery_date": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "total_amount": order.total_amount,  # integer paise (INR)
        "total_amount_formatted": format_inr(order.total_amount),
        "currency": order.currency or CURRENCY_CODE,
        "customer_id": order.customer_id,
        "seller_id": order.seller_id,
        "category": order.category,
    }


def get_customer_orders(db: Session, customer_id: int) -> List[Dict[str, Any]]:
    """
    Retrieves all orders associated with a customer ordered by order_date descending.
    Returns an empty list if the customer has no orders or does not exist.
    """
    if not customer_id or not isinstance(customer_id, int):
        return []

    orders = db.scalars(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.order_date.desc(), Order.id.desc())
    ).all()

    return [
        {
            "id": o.id,
            "order_number": o.order_number,
            "product_name": o.product_name,
            "order_status": o.order_status,
            "delivery_status": o.delivery_status,
            "order_date": o.order_date.isoformat() if o.order_date else None,
            "total_amount": o.total_amount,  # integer paise
            "total_amount_formatted": format_inr(o.total_amount),
            "currency": o.currency or CURRENCY_CODE,
            "seller_id": o.seller_id,
            "category": o.category,
        }
        for o in orders
    ]


def get_previous_complaints(db: Session, customer_id: int) -> List[Dict[str, Any]]:
    """
    Retrieves prior support cases for a customer, returning only fields necessary for support investigation.
    """
    if not customer_id or not isinstance(customer_id, int):
        return []

    cases = db.scalars(
        select(SupportCase)
        .where(SupportCase.customer_id == customer_id)
        .order_by(SupportCase.created_at.desc(), SupportCase.id.desc())
    ).all()

    return [
        {
            "id": c.id,
            "case_number": c.case_number,
            "order_id": c.order_id,
            "subject": c.subject,
            "status": c.status,
            "priority": c.priority,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cases
    ]


def get_case_details(db: Session, case_number: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves an existing support case and its stored operational details.
    """
    if not case_number or not isinstance(case_number, str):
        return None

    case = db.execute(
        select(SupportCase).where(SupportCase.case_number == case_number.strip())
    ).scalar_one_or_none()

    if not case:
        return None

    return {
        "id": case.id,
        "case_number": case.case_number,
        "customer_id": case.customer_id,
        "order_id": case.order_id,
        "subject": case.subject,
        "complaint_text": case.complaint_text,
        "status": case.status,
        "priority": case.priority,
        "resolution_summary": case.resolution_summary,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }


def get_refund_status(db: Session, order_number: str) -> Dict[str, Any]:
    """
    Inspects stored refund approval records related to the order.
    Returns explicit state 'not_recorded' or 'unknown' because no payment gateway
    or refund disbursement transaction table exists in the schema.
    """
    order = db.execute(
        select(Order).where(Order.order_number == order_number.strip())
    ).scalar_one_or_none()

    if not order:
        return {
            "order_found": False,
            "refund_status": "unknown",
            "approval_status": None,
            "limitation": f"Order '{order_number}' was not found in the database.",
        }

    # Check if any support case linked to this order has an approval request for refund
    approval = db.execute(
        select(ApprovalRequest)
        .join(SupportCase, ApprovalRequest.case_id == SupportCase.id)
        .where(
            SupportCase.order_id == order.id,
            ApprovalRequest.requested_action == "refund"
        )
    ).scalar_one_or_none()

    if approval:
        return {
            "order_found": True,
            "refund_status": "not_recorded",
            "approval_status": approval.status,
            "justification": approval.justification,
            "decision_reason": approval.decision_reason,
            "limitation": (
                "An internal approval record exists, but actual monetary payment disbursement cannot be "
                "confirmed because the database has no external payment processor transaction table."
            ),
        }

    return {
        "order_found": True,
        "refund_status": "not_recorded",
        "approval_status": "none",
        "limitation": "No refund approval or payment disbursement record exists in the system.",
    }


def create_support_ticket(db: Session, case_id: int, category: str) -> Dict[str, Any]:
    """
    Creates a real support ticket linked to an existing case.
    Validates case existence and category, generates unique ticket number,
    and returns stored result.
    """
    if not isinstance(case_id, int):
        raise ValueError("Invalid case_id: must be an integer.")

    category_clean = (category or "").strip()
    if not category_clean:
        raise ValueError("Ticket category must not be empty.")

    case = db.execute(
        select(SupportCase).where(SupportCase.id == case_id)
    ).scalar_one_or_none()

    if not case:
        raise ValueError(f"Support case with id={case_id} not found.")

    # Check for duplicate open ticket with identical category
    existing = db.execute(
        select(SupportTicket).where(
            SupportTicket.case_id == case_id,
            SupportTicket.category == category_clean,
            SupportTicket.status == "open",
        )
    ).scalar_one_or_none()

    if existing:
        return {
            "ticket_id": existing.id,
            "ticket_number": existing.ticket_number,
            "case_id": existing.case_id,
            "category": existing.category,
            "status": existing.status,
            "created_at": existing.created_at.isoformat(),
            "is_duplicate": True,
        }

    unique_suffix = uuid.uuid4().hex[:6].upper()
    ticket_number = f"TCK-{case_id}-{unique_suffix}"
    ticket = SupportTicket(
        ticket_number=ticket_number,
        case_id=case_id,
        category=category_clean,
        status="open",
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    try:
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
    except Exception as e:
        db.rollback()
        logger.error("Failed to persist support ticket: %s", e)
        raise

    return {
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "case_id": ticket.case_id,
        "category": ticket.category,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
        "is_duplicate": False,
    }


def update_case_status(db: Session, case_id: int, new_status: str) -> Dict[str, Any]:
    """
    Validates requested status against allowed values, updates the case,
    and atomically records a case event in the same transaction.
    """
    status_clean = (new_status or "").strip().lower()
    if status_clean not in ALLOWED_CASE_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Allowed statuses are: {sorted(list(ALLOWED_CASE_STATUSES))}"
        )

    case = db.execute(
        select(SupportCase).where(SupportCase.id == case_id)
    ).scalar_one_or_none()

    if not case:
        raise ValueError(f"Support case with id={case_id} not found.")

    old_status = case.status
    now = utc_now()
    case.status = status_clean
    case.updated_at = now

    event = CaseEvent(
        case_id=case_id,
        event_type="status_change",
        message=f"Case status changed from '{old_status}' to '{status_clean}'",
        details_json=None,
        created_at=now,
    )
    db.add(event)

    try:
        db.commit()
        db.refresh(case)
    except Exception as e:
        db.rollback()
        logger.error("Failed to update case status: %s", e)
        raise

    return {
        "case_id": case.id,
        "case_number": case.case_number,
        "old_status": old_status,
        "new_status": case.status,
        "updated_at": case.updated_at.isoformat(),
    }


def record_case_event(
    db: Session,
    case_id: int,
    event_type: str,
    message: str,
    details_json: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persists a case event ensuring case existence and transaction safety.
    """
    if not isinstance(case_id, int):
        raise ValueError("Invalid case_id: must be an integer.")

    event_type_clean = (event_type or "").strip()
    message_clean = (message or "").strip()

    if not event_type_clean or not message_clean:
        raise ValueError("Both event_type and message are required.")

    case = db.execute(
        select(SupportCase).where(SupportCase.id == case_id)
    ).scalar_one_or_none()

    if not case:
        raise ValueError(f"Support case with id={case_id} not found.")

    event = CaseEvent(
        case_id=case_id,
        event_type=event_type_clean,
        message=message_clean,
        details_json=details_json,
        created_at=utc_now(),
    )

    try:
        db.add(event)
        db.commit()
        db.refresh(event)
    except Exception as e:
        db.rollback()
        logger.error("Failed to record case event: %s", e)
        raise

    return {
        "id": event.id,
        "case_id": event.case_id,
        "event_type": event.event_type,
        "message": event.message,
        "created_at": event.created_at.isoformat(),
    }


def parse_policy_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Extracts YAML front matter metadata from a Markdown document if present.
    Returns (metadata_dict, body_text).
    """
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_meta = parts[1].strip()
            body = parts[2].strip()
            meta = {}
            for line in raw_meta.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if v.lower() == "true":
                        v = True
                    elif v.lower() == "false":
                        v = False
                    elif v.lower() == "null":
                        v = None
                    meta[k] = v
            return meta, body
    return {}, content


def search_policy_documents(
    query: str,
    policies_dir: Optional[Path] = None,
    seller_id: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs real local keyword-based search across Markdown files in data/policies.
    Parses front matter metadata and filters by seller_id or category if specified.
    Returns matched document passages with filename, line numbers, policy_id, and scope.
    Does not claim to be vector RAG.
    """
    query_clean = (query or "").strip().lower()
    search_dir = policies_dir or (settings.project_root / "data" / "policies")

    if not query_clean:
        return {
            "query": query,
            "matches": [],
            "total_matches": 0,
            "message": "Empty query provided.",
        }

    if not search_dir.exists() or not search_dir.is_dir():
        return {
            "query": query,
            "matches": [],
            "total_matches": 0,
            "message": f"Policy directory '{search_dir}' not found.",
        }

    terms = set(re.findall(r"\w+", query_clean))
    stop_words = {"the", "a", "an", "is", "for", "and", "or", "in", "to", "of", "with", "my", "on", "at"}
    terms = {t for t in terms if t not in stop_words and len(t) > 2}

    if not terms:
        terms = {query_clean}

    matches: List[Dict[str, Any]] = []

    for md_file in sorted(search_dir.glob("*.md")):
        try:
            full_content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Could not read policy file %s: %s", md_file.name, e)
            continue

        meta, body = parse_policy_frontmatter(full_content)

        # Apply optional filters
        if seller_id and meta.get("seller_id") and meta.get("seller_id") != seller_id:
            continue
        if category and meta.get("category") and meta.get("category") != category:
            continue

        paragraphs = body.split("\n\n")
        line_offset = 1

        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                line_offset += p.count("\n") + 2
                continue

            p_lower = p_clean.lower()
            matched_terms = [t for t in terms if t in p_lower]

            if matched_terms:
                matches.append({
                    "document_name": md_file.name,
                    "policy_id": meta.get("policy_id"),
                    "scope": meta.get("scope"),
                    "seller_id": meta.get("seller_id"),
                    "category": meta.get("category"),
                    "passage": p_clean,
                    "matched_terms": matched_terms,
                    "line_number": line_offset,
                })

            line_offset += p.count("\n") + 2

    return {
        "query": query,
        "matches": matches,
        "passages": matches,
        "total_matches": len(matches),
        "count": len(matches),
        "message": f"Found {len(matches)} relevant passage(s) across policies.",
    }


def check_refund_eligibility(db: Session, order_number: str) -> Dict[str, Any]:
    """
    Assesses refund eligibility conservatively and deterministically based on
    actual stored order facts and canonical synthetic policy rules in Indian Rupees (INR).
    All internal monetary evaluations use integer paise.
    Does NOT execute a refund or promise disbursement.
    """
    order = db.execute(
        select(Order).where(Order.order_number == order_number.strip())
    ).scalar_one_or_none()

    if not order:
        return {
            "order_number": order_number,
            "decision": "needs_review",
            "order_facts": {},
            "policy_evidence": "No matching order found in database.",
            "reasons": [f"Order '{order_number}' does not exist."],
            "missing_information": ["Valid order record"],
            "human_approval_required": True,
        }

    formatted_amount = format_inr(order.total_amount)
    order_facts = {
        "order_number": order.order_number,
        "product_name": order.product_name,
        "order_status": order.order_status,
        "delivery_status": order.delivery_status,
        "total_amount_paise": order.total_amount,
        "total_amount_formatted": formatted_amount,
        "currency": order.currency or CURRENCY_CODE,
        "seller_id": order.seller_id,
        "category": order.category,
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
    }

    reasons: List[str] = []
    missing_info: List[str] = []
    policy_evidence = ""
    human_approval_required = False
    decision = "needs_review"

    # Category-specific or default return window
    allowed_window_days = CATEGORY_RETURN_WINDOWS.get(order.category, DEFAULT_RETURN_WINDOW_DAYS)

    # Evaluate delivery status
    if order.delivery_status == "delivered":
        if not order.delivered_at:
            missing_info.append("Verified delivered_at timestamp")
            decision = "needs_review"
            reasons.append("Order marked delivered but delivered_at timestamp is unrecorded.")
            human_approval_required = True
        else:
            deliv_dt = order.delivered_at
            if deliv_dt.tzinfo is None:
                deliv_dt = deliv_dt.replace(tzinfo=timezone.utc)
            now = utc_now()
            days_since_delivery = (now - deliv_dt).days

            if days_since_delivery <= allowed_window_days:
                policy_evidence = f"Canonical Return Policy: Return window is {allowed_window_days} calendar days from confirmed delivery."

                # Compare against centralized Tier 1 limit in paise (₹5,000.00 / 5,00,000 paise)
                if order.total_amount <= TIER_1_MAX_AMOUNT_PAISE:
                    decision = "eligible"
                    reasons.append(
                        f"Delivered {days_since_delivery} days ago (within {allowed_window_days}-day window) and "
                        f"amount {formatted_amount} is within Tier 1 automated threshold ({format_inr(TIER_1_MAX_AMOUNT_PAISE)})."
                    )
                else:
                    decision = "needs_review"
                    human_approval_required = True
                    reasons.append(
                        f"Delivered {days_since_delivery} days ago (within {allowed_window_days}-day window), but "
                        f"amount {formatted_amount} exceeds Tier 1 threshold ({format_inr(TIER_1_MAX_AMOUNT_PAISE)}), requiring Tier 2 supervisor approval."
                    )
            else:
                decision = "ineligible"
                policy_evidence = f"Canonical Return Policy: Claims past {allowed_window_days} days are outside standard return eligibility."
                reasons.append(
                    f"Delivered {days_since_delivery} days ago, exceeding the {allowed_window_days}-day policy window."
                )
                human_approval_required = True

    elif order.delivery_status in ("delayed", "not_shipped"):
        decision = "needs_review"
        human_approval_required = True
        policy_evidence = "Platform Shipping Policy Section 2: Delayed/undelivered shipments require logistics carrier investigation."
        reasons.append(
            f"Order delivery status is '{order.delivery_status}'. Refund eligibility cannot be granted automatically without carrier investigation."
        )
    else:
        decision = "needs_review"
        human_approval_required = True
        reasons.append(f"Unusual delivery status '{order.delivery_status}' requires manual supervisor review.")

    return {
        "order_number": order.order_number,
        "decision": decision,
        "order_facts": order_facts,
        "policy_evidence": policy_evidence,
        "reasons": reasons,
        "missing_information": missing_info,
        "human_approval_required": human_approval_required,
    }


# ---------------------------------------------------------------------------
# Level 5: Human Approval & Review Database Helpers
# ---------------------------------------------------------------------------

def create_or_update_approval_request(
    db: Session,
    case_id: int,
    thread_id: Optional[str],
    requested_action: str,
    justification: str,
    proposed_resolution: Optional[str] = None,
    policy_evidence: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates or updates an ApprovalRequest record linked to a support case.
    Sets status to 'pending' and workflow_status to 'pending_review'.
    """
    case = db.execute(
        select(SupportCase).where(SupportCase.id == case_id)
    ).scalar_one_or_none()

    if not case:
        raise ValueError(f"Support case with id={case_id} not found.")

    # Check for existing pending approval request for this case
    existing = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.case_id == case_id,
            ApprovalRequest.status == "pending",
        )
    ).scalar_one_or_none()

    now = utc_now()
    order_amount = case.order.total_amount if case and case.order else None
    sla_info = calculate_sla_parameters(order_amount_paise=order_amount, created_at=now)

    if existing:
        existing.thread_id = thread_id or existing.thread_id
        existing.requested_action = requested_action
        existing.justification = justification
        existing.proposed_resolution = proposed_resolution
        existing.policy_evidence = policy_evidence
        if existing.expires_at is None:
            existing.expires_at = sla_info["expires_at"]
            existing.sla_priority = sla_info["sla_priority"]
            existing.required_role = sla_info["required_role"]
        existing.updated_at = now
        approval = existing
    else:
        approval = ApprovalRequest(
            case_id=case_id,
            thread_id=thread_id,
            requested_action=requested_action,
            status="pending",
            workflow_status="pending_review",
            justification=justification,
            proposed_resolution=proposed_resolution,
            policy_evidence=policy_evidence,
            expires_at=sla_info["expires_at"],
            sla_priority=sla_info["sla_priority"],
            required_role=sla_info["required_role"],
            is_expired=False,
            created_at=now,
            updated_at=now,
        )
        db.add(approval)

    try:
        db.commit()
        db.refresh(approval)
    except Exception as e:
        db.rollback()
        logger.error("Failed to persist approval request: %s", e)
        raise

    return {
        "id": approval.id,
        "case_id": approval.case_id,
        "thread_id": approval.thread_id,
        "requested_action": approval.requested_action,
        "status": approval.status,
        "workflow_status": approval.workflow_status,
        "justification": approval.justification,
        "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        "sla_priority": approval.sla_priority,
        "required_role": approval.required_role,
        "is_expired": bool(approval.is_expired),
        "created_at": approval.created_at.isoformat(),
        "updated_at": approval.updated_at.isoformat(),
    }


def get_pending_approval_requests(
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Retrieves paginated list of approval requests awaiting supervisor review.
    Evaluates pending SLAs to mark overdue requests and records audit events.
    Enriches items with SLA metadata, case number, complaint text, and order details.
    """
    from sqlalchemy import func

    # Scan and update SLA expiration status for pending requests
    evaluate_pending_approvals_slas(db)

    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    count_query = select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == "pending")
    total_count = db.scalar(count_query) or 0

    query = (
        select(ApprovalRequest)
        .where(ApprovalRequest.status == "pending")
        .order_by(ApprovalRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    records = db.scalars(query).all()

    items = []
    for r in records:
        case = r.case
        order_number = None
        customer_name = None
        if case:
            if case.order:
                order_number = case.order.order_number
            if case.customer:
                customer_name = case.customer.name

        items.append({
            "id": r.id,
            "case_id": r.case_id,
            "case_number": case.case_number if case else None,
            "order_number": order_number,
            "customer_name": customer_name,
            "thread_id": r.thread_id,
            "requested_action": r.requested_action,
            "status": r.status,
            "workflow_status": r.workflow_status,
            "justification": r.justification,
            "proposed_resolution": r.proposed_resolution,
            "policy_evidence": r.policy_evidence,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "sla_priority": r.sla_priority or "standard",
            "required_role": r.required_role or "tier2_supervisor",
            "is_expired": bool(r.is_expired),
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        })

    return {
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


def get_approval_request_by_thread_id(
    db: Session,
    thread_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieves full details of an approval request by its LangGraph thread_id,
    including SLA metadata and current expiration status.
    """
    if not thread_id or not isinstance(thread_id, str):
        return None

    approval = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.thread_id == thread_id.strip())
    ).scalar_one_or_none()

    if not approval:
        return None

    # Evaluate SLA for pending request
    if approval.status == "pending":
        evaluate_and_record_sla_breach(db, approval)
        db.commit()
        db.refresh(approval)

    case = approval.case
    order_info = None
    customer_info = None
    if case:
        if case.order:
            order_info = {
                "order_number": case.order.order_number,
                "product_name": case.order.product_name,
                "total_amount": case.order.total_amount,
                "currency": case.order.currency,
                "delivery_status": case.order.delivery_status,
            }
        if case.customer:
            customer_info = {
                "name": case.customer.name,
                "email": case.customer.email,
            }

    return {
        "id": approval.id,
        "case_id": approval.case_id,
        "case_number": case.case_number if case else None,
        "thread_id": approval.thread_id,
        "requested_action": approval.requested_action,
        "status": approval.status,
        "workflow_status": approval.workflow_status,
        "justification": approval.justification,
        "proposed_resolution": approval.proposed_resolution,
        "policy_evidence": approval.policy_evidence,
        "reviewer_id": approval.reviewer_id,
        "decision_reason": approval.decision_reason,
        "decision_timestamp": approval.decision_timestamp.isoformat() if approval.decision_timestamp else None,
        "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        "sla_priority": approval.sla_priority or "standard",
        "required_role": approval.required_role or "tier2_supervisor",
        "is_expired": bool(approval.is_expired),
        "created_at": approval.created_at.isoformat(),
        "updated_at": approval.updated_at.isoformat(),
        "case": {
            "id": case.id if case else None,
            "case_number": case.case_number if case else None,
            "subject": case.subject if case else None,
            "complaint_text": case.complaint_text if case else None,
            "status": case.status if case else None,
            "priority": case.priority if case else None,
        } if case else None,
        "order": order_info,
        "customer": customer_info,
    }


def record_approval_decision(
    db: Session,
    thread_id: str,
    decision: str,  # 'approved' or 'rejected'
    reviewer_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Atomically records a supervisor's approval or rejection decision.
    Validates that the request is currently in 'pending' status.
    Updates case and records audit event in the same transaction.
    """
    decision_clean = (decision or "").strip().lower()
    if decision_clean not in ("approved", "rejected"):
        raise ValueError(f"Invalid decision '{decision}'. Must be 'approved' or 'rejected'.")

    reviewer_clean = (reviewer_id or "").strip()
    if not reviewer_clean:
        raise ValueError("Reviewer identifier is required.")

    if decision_clean == "rejected" and not (reason or "").strip():
        raise ValueError("A non-empty rejection reason is required when rejecting a case.")

    approval = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.thread_id == thread_id.strip())
    ).scalar_one_or_none()

    if not approval:
        raise ValueError(f"Approval request for thread_id '{thread_id}' not found.")

    if approval.status != "pending":
        raise ValueError(
            f"Approval request is not pending. Current status: '{approval.status}' "
            f"(decided by '{approval.reviewer_id}' at {approval.decision_timestamp})."
        )

    now = utc_now()
    approval.status = decision_clean
    approval.workflow_status = decision_clean
    approval.reviewer_id = reviewer_clean
    approval.decision_reason = reason.strip() if reason else None
    approval.decision_timestamp = now
    approval.updated_at = now

    event_type = "approval_granted" if decision_clean == "approved" else "approval_rejected"
    msg = (
        f"Supervisor '{reviewer_clean}' {decision_clean} the proposed resolution"
        + (f": {reason.strip()}" if reason and reason.strip() else ".")
    )

    evt = CaseEvent(
        case_id=approval.case_id,
        event_type=event_type,
        message=msg,
        details_json=None,
        created_at=now,
    )
    db.add(evt)

    # Update support case status if rejected
    if decision_clean == "rejected" and approval.case:
        approval.case.status = "escalated"
        approval.case.resolution_summary = f"Supervisor rejected resolution: {reason.strip()}"
        approval.case.updated_at = now

    try:
        db.commit()
        db.refresh(approval)
    except Exception as e:
        db.rollback()
        logger.error("Failed to record approval decision: %s", e)
        raise

    return {
        "id": approval.id,
        "case_id": approval.case_id,
        "thread_id": approval.thread_id,
        "status": approval.status,
        "workflow_status": approval.workflow_status,
        "reviewer_id": approval.reviewer_id,
        "decision_reason": approval.decision_reason,
        "decision_timestamp": approval.decision_timestamp.isoformat(),
        "event_recorded": event_type,
    }


# ---------------------------------------------------------------------------
# Level 6 Phase 4: Customer Clarification Queue Helpers
# ---------------------------------------------------------------------------

def get_pending_clarifications(
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Retrieves paginated list of workflows awaiting customer clarification.
    Inspects LangGraph checkpointer for threads paused at 'customer_clarification'
    with status 'needs_information', and enriches records with case, customer, and order data.
    """
    from app.workflows import get_resolution_graph
    from app.workflows.checkpointer import get_checkpointer

    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    graph = get_resolution_graph()
    cp = get_checkpointer()
    cur = cp.conn.cursor()
    cur.execute("SELECT DISTINCT thread_id FROM checkpoints")
    threads = [row[0] for row in cur.fetchall()]

    waiting_items = []
    for tid in threads:
        try:
            state = graph.get_state({"configurable": {"thread_id": tid}})
            if not state or not state.values:
                continue
            values = state.values
            wf_status = values.get("workflow_status")
            next_nodes = state.next or ()
            if wf_status == "needs_information" and "customer_clarification" in next_nodes:
                case_id = values.get("case_id")
                case_num = values.get("case_number")
                cust_id = values.get("customer_id")
                order_num = values.get("order_number")
                complaint_text = values.get("customer_complaint") or ""

                customer_name = None
                customer_email = None

                # Enrich with database records if case_id or cust_id present
                if case_id:
                    case_obj = db.execute(select(SupportCase).where(SupportCase.id == case_id)).scalar_one_or_none()
                    if case_obj:
                        case_num = case_obj.case_number or case_num
                        if cust_id is None:
                            cust_id = case_obj.customer_id
                        if not complaint_text:
                            complaint_text = case_obj.complaint_text or ""
                        if case_obj.order and not order_num:
                            order_num = case_obj.order.order_number

                if cust_id:
                    cust_obj = db.execute(select(Customer).where(Customer.id == cust_id)).scalar_one_or_none()
                    if cust_obj:
                        customer_name = cust_obj.name
                        customer_email = cust_obj.email

                waiting_items.append({
                    "thread_id": tid,
                    "case_id": case_id,
                    "case_number": case_num or (f"CASE-{case_id}" if case_id else "N/A"),
                    "order_number": order_num,
                    "customer_id": cust_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "complaint_text": complaint_text,
                    "status": "needs_information",
                    "workflow_status": "needs_information",
                    "missing_information": values.get("missing_information", []),
                    "clarification_details": values.get("clarification_details") or {},
                    "clarification_count": values.get("clarification_count", 0),
                    "created_at": values.get("created_at"),
                    "updated_at": values.get("updated_at"),
                })
        except Exception as e:
            logger.warning("Error inspecting checkpoint state for thread %s: %s", tid, e)
            continue

    waiting_items.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
    total_count = len(waiting_items)
    paginated_items = waiting_items[offset : offset + limit]

    return {
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "items": paginated_items,
    }


def get_clarification_by_thread_id(
    db: Session,
    thread_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieves full details of a workflow thread awaiting customer clarification.
    """
    from app.workflows import get_resolution_graph

    if not thread_id or not isinstance(thread_id, str):
        return None

    clean_thread = thread_id.strip()
    try:
        graph = get_resolution_graph()
        state = graph.get_state({"configurable": {"thread_id": clean_thread}})
        if not state or not state.values:
            return None
        values = state.values
        wf_status = values.get("workflow_status")
        next_nodes = state.next or ()
        if wf_status != "needs_information" or "customer_clarification" not in next_nodes:
            return None

        case_id = values.get("case_id")
        case_num = values.get("case_number")
        cust_id = values.get("customer_id")
        order_num = values.get("order_number")
        complaint_text = values.get("customer_complaint") or ""

        case_info = None
        customer_info = None
        order_info = None

        if case_id:
            case_obj = db.execute(select(SupportCase).where(SupportCase.id == case_id)).scalar_one_or_none()
            if case_obj:
                case_num = case_obj.case_number or case_num
                if cust_id is None:
                    cust_id = case_obj.customer_id
                if not complaint_text:
                    complaint_text = case_obj.complaint_text or ""
                case_info = {
                    "id": case_obj.id,
                    "case_number": case_obj.case_number,
                    "status": case_obj.status,
                    "complaint_text": case_obj.complaint_text,
                    "created_at": case_obj.created_at.isoformat(),
                }
                if case_obj.order and not order_num:
                    order_num = case_obj.order.order_number

        if cust_id:
            cust_obj = db.execute(select(Customer).where(Customer.id == cust_id)).scalar_one_or_none()
            if cust_obj:
                customer_info = {
                    "id": cust_obj.id,
                    "name": cust_obj.name,
                    "email": cust_obj.email,
                    "phone": cust_obj.phone,
                }

        if order_num:
            order_obj = db.execute(select(Order).where(Order.order_number == order_num)).scalar_one_or_none()
            if order_obj:
                order_info = {
                    "id": order_obj.id,
                    "order_number": order_obj.order_number,
                    "product_name": order_obj.product_name,
                    "total_amount": order_obj.total_amount,
                    "delivery_status": order_obj.delivery_status,
                }

        return {
            "thread_id": clean_thread,
            "case_id": case_id,
            "case_number": case_num or (f"CASE-{case_id}" if case_id else "N/A"),
            "order_number": order_num,
            "customer_id": cust_id,
            "customer_name": customer_info["name"] if customer_info else None,
            "customer_email": customer_info["email"] if customer_info else None,
            "complaint_text": complaint_text,
            "status": "needs_information",
            "workflow_status": "needs_information",
            "missing_information": values.get("missing_information", []),
            "clarification_details": values.get("clarification_details") or {},
            "clarification_count": values.get("clarification_count", 0),
            "created_at": values.get("created_at"),
            "updated_at": values.get("updated_at"),
            "case": case_info,
            "customer": customer_info,
            "order": order_info,
        }
    except Exception as e:
        logger.error("Error retrieving clarification details for thread %s: %s", clean_thread, e)
        return None


def get_case_events(
    db: Session,
    case_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Retrieves chronological audit history events for a given support case.
    """
    if not isinstance(case_id, int):
        return []

    events = db.scalars(
        select(CaseEvent)
        .where(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.created_at.asc(), CaseEvent.id.asc())
        .limit(min(max(1, limit), 100))
        .offset(max(0, offset))
    ).all()

    return [
        {
            "id": evt.id,
            "case_id": evt.case_id,
            "event_type": evt.event_type,
            "message": evt.message,
            "details_json": evt.details_json,
            "created_at": evt.created_at.isoformat() if evt.created_at else None,
        }
        for evt in events
    ]


def get_analytics_summary(db: Session) -> Dict[str, Any]:
    """
    Computes real-time operational metrics directly aggregated from database tables.
    Never returns fabricated metrics or hardcoded counts.
    """
    total_cases = db.scalar(select(func.count(SupportCase.id))) or 0
    open_cases = db.scalar(select(func.count(SupportCase.id)).where(SupportCase.status == "open")) or 0
    in_prog_cases = db.scalar(select(func.count(SupportCase.id)).where(SupportCase.status == "in_progress")) or 0
    resolved_cases = db.scalar(select(func.count(SupportCase.id)).where(SupportCase.status == "resolved")) or 0
    closed_cases = db.scalar(select(func.count(SupportCase.id)).where(SupportCase.status == "closed")) or 0
    escalated_cases = db.scalar(select(func.count(SupportCase.id)).where(SupportCase.status == "escalated")) or 0

    pending_approvals = db.scalar(
        select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == "pending")
    ) or 0
    approved_count = db.scalar(
        select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == "approved")
    ) or 0
    rejected_count = db.scalar(
        select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == "rejected")
    ) or 0
    sla_breaches = db.scalar(
        select(func.count(ApprovalRequest.id)).where(ApprovalRequest.is_expired.is_(True))
    ) or 0

    # Pending clarifications count
    pending_clarifications_data = get_pending_clarifications(db, limit=100)
    pending_clarifications = pending_clarifications_data.get("total", 0)

    # Category distribution from Orders
    category_counts = db.execute(
        select(Order.category, func.count(Order.id))
        .where(Order.category.isnot(None))
        .group_by(Order.category)
    ).all()
    category_distribution = [
        {"category": cat or "general", "count": count}
        for cat, count in category_counts
    ]

    status_distribution = [
        {"status": "open", "count": open_cases},
        {"status": "in_progress", "count": in_prog_cases},
        {"status": "resolved", "count": resolved_cases},
        {"status": "closed", "count": closed_cases},
        {"status": "escalated", "count": escalated_cases},
    ]

    recent_case_objs = db.scalars(
        select(SupportCase)
        .order_by(SupportCase.created_at.desc())
        .limit(10)
    ).all()
    recent_activity = [
        {
            "case_number": c.case_number,
            "subject": c.subject,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in recent_case_objs
    ]

    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "in_progress_cases": in_prog_cases,
        "resolved_cases": resolved_cases,
        "closed_cases": closed_cases,
        "escalated_cases": escalated_cases,
        "pending_approvals": pending_approvals,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "sla_breaches": sla_breaches,
        "pending_clarifications": pending_clarifications,
        "category_distribution": category_distribution,
        "status_distribution": status_distribution,
        "recent_activity": recent_activity,
    }

