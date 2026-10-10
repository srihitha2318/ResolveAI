"""
Approval SLA Management Subsystem for ResolveAI.
Provides operational SLA calculation, deadline tracking, idempotent breach evaluation,
auditable event logging, and protected authorization rules for expired approval requests.
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import ROLE_SENIOR_SUPERVISOR, ROLE_TIER2_SUPERVISOR
from app.core.config import settings
from app.core.logging_config import logger
from app.core.policy_rules import HIGH_VALUE_THRESHOLD_PAISE
from app.database.models import ApprovalRequest, CaseEvent

# SLA Priority Constants
SLA_PRIORITY_STANDARD = "standard"
SLA_PRIORITY_HIGH = "high"


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Normalizes a datetime instance to timezone-aware UTC.
    If naive, assumes UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_sla_parameters(
    order_amount_paise: Optional[int] = None,
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Calculates operational SLA deadline, priority, and required reviewer role.
    Assigns:
      - Standard (Tier 2): order_amount <= ₹25,000 -> 12 hours (configurable)
      - High-Value: order_amount > ₹25,000 -> 4 hours (configurable)
    All timestamps are strictly calculated in UTC.
    """
    is_high_value = (
        order_amount_paise is not None
        and order_amount_paise > HIGH_VALUE_THRESHOLD_PAISE
    )

    if is_high_value:
        priority = SLA_PRIORITY_HIGH
        required_role = ROLE_SENIOR_SUPERVISOR
        sla_hours = settings.SLA_HIGH_VALUE_HOURS
    else:
        priority = SLA_PRIORITY_STANDARD
        required_role = ROLE_TIER2_SUPERVISOR
        sla_hours = settings.SLA_STANDARD_HOURS

    base_time = ensure_utc(created_at) or datetime.now(timezone.utc)
    expires_at = base_time + timedelta(hours=sla_hours)

    return {
        "expires_at": expires_at,
        "sla_priority": priority,
        "required_role": required_role,
        "sla_hours": sla_hours,
        "is_high_value": is_high_value,
    }


def is_approval_expired(
    approval: ApprovalRequest,
    current_time: Optional[datetime] = None,
) -> bool:
    """
    Evaluates whether an approval request has breached its SLA expiration timestamp.
    Safely handles both timezone-aware and timezone-naive timestamps.
    """
    if approval.is_expired:
        return True

    if approval.expires_at is None:
        return False

    now = ensure_utc(current_time) or datetime.now(timezone.utc)
    exp = ensure_utc(approval.expires_at)
    return now >= exp


def get_time_remaining_seconds(
    approval: ApprovalRequest,
    current_time: Optional[datetime] = None,
) -> Optional[int]:
    """
    Returns signed seconds remaining before SLA expiration.
    Negative value indicates seconds overdue.
    """
    if approval.expires_at is None:
        return None

    now = ensure_utc(current_time) or datetime.now(timezone.utc)
    exp = ensure_utc(approval.expires_at)
    return int((exp - now).total_seconds())


def evaluate_and_record_sla_breach(
    db: Session,
    approval: ApprovalRequest,
    current_time: Optional[datetime] = None,
) -> bool:
    """
    Evaluates a pending approval request for SLA breach.
    If overdue and pending:
      1. Idempotently marks approval.is_expired = True.
      2. Records an auditable 'sla_breached' CaseEvent (if not already recorded).
    Returns True if a new breach was recorded or marked; False otherwise.
    Never alters approval status (remains 'pending') or executes any financial operations.
    """
    if approval.status != "pending":
        return False

    if not is_approval_expired(approval, current_time=current_time):
        return False

    now = ensure_utc(current_time) or datetime.now(timezone.utc)
    newly_marked = False

    if not approval.is_expired:
        approval.is_expired = True
        approval.updated_at = now
        newly_marked = True

    # Check for existing breach event to avoid duplicates
    existing_event = db.execute(
        select(CaseEvent).where(
            CaseEvent.case_id == approval.case_id,
            CaseEvent.event_type == "sla_breached",
        )
    ).first()

    if not existing_event:
        exp_iso = approval.expires_at.isoformat() if approval.expires_at else "unknown"
        evt = CaseEvent(
            case_id=approval.case_id,
            event_type="sla_breached",
            message=(
                f"Approval request #{approval.id} breached target SLA deadline ({exp_iso}). "
                f"Escalation priority: {approval.sla_priority}, Required reviewer role: {approval.required_role}."
            ),
            details_json=json.dumps({
                "approval_id": approval.id,
                "thread_id": approval.thread_id,
                "expires_at": exp_iso,
                "sla_priority": approval.sla_priority,
                "required_role": approval.required_role,
                "breached_at": now.isoformat(),
            }),
            created_at=now,
        )
        db.add(evt)
        newly_marked = True

    return newly_marked


def evaluate_pending_approvals_slas(
    db: Session,
    current_time: Optional[datetime] = None,
) -> int:
    """
    Scans all pending approval requests in the database and updates SLA breach statuses.
    Commits updates and returns count of newly recorded breaches.
    """
    now = ensure_utc(current_time) or datetime.now(timezone.utc)
    pending_records = db.scalars(
        select(ApprovalRequest).where(
            ApprovalRequest.status == "pending",
            ApprovalRequest.expires_at.is_not(None),
        )
    ).all()

    breached_count = 0
    for record in pending_records:
        if evaluate_and_record_sla_breach(db, record, current_time=now):
            breached_count += 1

    if breached_count > 0:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Failed committing pending approvals SLA evaluation: %s", e)
            raise

    return breached_count


def validate_approval_decision_sla(
    approval: ApprovalRequest,
    reviewer_role: str,
    override_expired: bool = False,
    current_time: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validates whether the reviewer is authorized to decide on the approval request given its SLA state.
    Rules:
      - If not expired: Ordinary approval flow proceeds as usual.
      - If expired:
          * Frontline agents and Tier 2 supervisors CANNOT approve or reject (403).
          * Senior supervisors MUST explicitly specify override_expired=True (400 if False).
          * Senior supervisors with override_expired=True are authorized to proceed.
    """
    expired = is_approval_expired(approval, current_time=current_time)
    if not expired:
        return True, None

    if reviewer_role != ROLE_SENIOR_SUPERVISOR:
        return (
            False,
            f"Approval request #{approval.id} has breached its SLA deadline ({approval.expires_at.isoformat() if approval.expires_at else 'expired'}). "
            f"Processing expired approval requests requires senior supervisor authorization."
        )

    if not override_expired:
        return (
            False,
            f"Approval request #{approval.id} has breached its SLA deadline. "
            f"Senior supervisor processing requires explicit override confirmation ('override_expired': true)."
        )

    return True, None
