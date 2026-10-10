from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Customer, Order, SupportCase, SupportTicket, CaseEvent, utc_now
from app.database.seed import seed_database
from app.tools.support_tools import (
    get_order_details,
    get_customer_orders,
    get_case_details,
    get_refund_status,
    create_support_ticket,
    update_case_status,
    record_case_event,
    check_refund_eligibility,
)


def test_create_support_ticket_valid(test_db: Session):
    """Verify creating a support ticket for a valid case."""
    seed_database(test_db)
    case = test_db.execute(select(SupportCase)).scalars().first()

    ticket_res = create_support_ticket(test_db, case_id=case.id, category="general_inquiry")

    assert ticket_res["ticket_id"] is not None
    assert ticket_res["case_id"] == case.id
    assert ticket_res["category"] == "general_inquiry"
    assert ticket_res["is_duplicate"] is False

    # Check database persistence
    stored = test_db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_res["ticket_id"])
    ).scalar_one_or_none()
    assert stored is not None
    assert stored.ticket_number == ticket_res["ticket_number"]


def test_create_support_ticket_invalid_case(test_db: Session):
    """Verify error when creating ticket for non-existent case."""
    with pytest.raises(ValueError, match="not found"):
        create_support_ticket(test_db, case_id=999999, category="billing")


def test_create_support_ticket_duplicate_behavior(test_db: Session):
    """Verify duplicate ticket creation returns existing ticket without duplicating."""
    seed_database(test_db)
    case = test_db.execute(select(SupportCase)).scalars().first()

    first_ticket = create_support_ticket(test_db, case_id=case.id, category="duplicate_test")
    assert first_ticket["is_duplicate"] is False

    second_ticket = create_support_ticket(test_db, case_id=case.id, category="duplicate_test")
    assert second_ticket["is_duplicate"] is True
    assert second_ticket["ticket_id"] == first_ticket["ticket_id"]


def test_update_case_status_valid(test_db: Session):
    """Verify valid case status update updates timestamp and records a status_change event."""
    seed_database(test_db)
    case = test_db.execute(select(SupportCase).where(SupportCase.status == "open")).scalars().first()

    res = update_case_status(test_db, case_id=case.id, new_status="in_progress")
    assert res["new_status"] == "in_progress"

    # Verify event was recorded atomically
    event = test_db.execute(
        select(CaseEvent)
        .where(CaseEvent.case_id == case.id, CaseEvent.event_type == "status_change")
        .order_by(CaseEvent.created_at.desc())
    ).scalars().first()

    assert event is not None
    assert "in_progress" in event.message


def test_update_case_status_invalid(test_db: Session):
    """Verify rejection of invalid status."""
    seed_database(test_db)
    case = test_db.execute(select(SupportCase)).scalars().first()

    with pytest.raises(ValueError, match="Invalid status"):
        update_case_status(test_db, case_id=case.id, new_status="completely_invalid_status")


def test_update_case_status_missing_case(test_db: Session):
    """Verify error on updating non-existent case."""
    with pytest.raises(ValueError, match="not found"):
        update_case_status(test_db, case_id=88888, new_status="resolved")


def test_record_case_event(test_db: Session):
    """Verify persisting audit event on a case."""
    seed_database(test_db)
    case = test_db.execute(select(SupportCase)).scalars().first()

    ev = record_case_event(
        test_db,
        case_id=case.id,
        event_type="agent_note",
        message="Investigated customer inquiry",
    )
    assert ev["id"] is not None
    assert ev["event_type"] == "agent_note"


def test_refund_status_no_fake_refund(test_db: Session):
    """Verify refund status returns 'not_recorded' and explains lack of payment gateway table."""
    seed_database(test_db)
    status_info = get_refund_status(test_db, "ORD-2026-001")

    assert status_info["order_found"] is True
    assert status_info["refund_status"] == "not_recorded"
    assert "payment" in status_info["limitation"].lower()


def test_check_refund_eligibility_scenarios(test_db: Session):
    """Verify conservative refund eligibility across eligible, ineligible, and high-value scenarios in INR."""
    now = utc_now()
    cust = Customer(name="Test Refund Cust", email="refundtest@example.com", created_at=now)
    test_db.add(cust)
    test_db.flush()

    # 1. Eligible order: delivered 5 days ago, under Tier 1 threshold (₹2,500.00 = 250000 paise)
    order_eligible = Order(
        order_number="ORD-ELIGIBLE-01",
        customer_id=cust.id,
        product_name="Eligible Headset",
        order_status="delivered",
        delivery_status="delivered",
        order_date=now - timedelta(days=10),
        expected_delivery_date=now - timedelta(days=6),
        delivered_at=now - timedelta(days=5),
        total_amount=250000,  # ₹2,500.00
        currency="INR",
        created_at=now - timedelta(days=10),
    )
    test_db.add(order_eligible)

    # 2. Ineligible order: delivered 45 days ago (> 30 days window)
    order_ineligible = Order(
        order_number="ORD-INELIGIBLE-02",
        customer_id=cust.id,
        product_name="Old Purchase",
        order_status="delivered",
        delivery_status="delivered",
        order_date=now - timedelta(days=50),
        expected_delivery_date=now - timedelta(days=46),
        delivered_at=now - timedelta(days=45),
        total_amount=150000,  # ₹1,500.00
        currency="INR",
        created_at=now - timedelta(days=50),
    )
    test_db.add(order_ineligible)

    # 3. High value order: delivered 3 days ago, but ₹35,000.00 (3500000 paise, exceeds ₹5,000 Tier 1)
    order_high_val = Order(
        order_number="ORD-HIGHVAL-03",
        customer_id=cust.id,
        product_name="High End Laptop",
        order_status="delivered",
        delivery_status="delivered",
        order_date=now - timedelta(days=8),
        expected_delivery_date=now - timedelta(days=4),
        delivered_at=now - timedelta(days=3),
        total_amount=3500000,  # ₹35,000.00
        currency="INR",
        created_at=now - timedelta(days=8),
    )
    test_db.add(order_high_val)
    test_db.commit()

    # Check eligible
    el_res = check_refund_eligibility(test_db, "ORD-ELIGIBLE-01")
    assert el_res["decision"] == "eligible"
    assert el_res["human_approval_required"] is False
    assert el_res["order_facts"]["currency"] == "INR"
    assert "₹2,500.00" in el_res["order_facts"]["total_amount_formatted"]

    # Check ineligible
    inel_res = check_refund_eligibility(test_db, "ORD-INELIGIBLE-02")
    assert inel_res["decision"] == "ineligible"

    # Check high value needs review
    hv_res = check_refund_eligibility(test_db, "ORD-HIGHVAL-03")
    assert hv_res["decision"] == "needs_review"
    assert hv_res["human_approval_required"] is True

    # Check non-existent order
    ghost_res = check_refund_eligibility(test_db, "ORD-NONEXISTENT")
    assert ghost_res["decision"] == "needs_review"
    assert "Valid order record" in ghost_res["missing_information"]
