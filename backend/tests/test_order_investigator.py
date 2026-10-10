from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.agents.order_investigator import OrderInvestigatorAgent
from app.database.models import Customer, Order, SupportCase, utc_now
from app.database.seed import seed_database
from app.schemas.agent_schemas import OrderInvestigationInput


@pytest.fixture
def investigator():
    return OrderInvestigatorAgent()


def test_investigate_existing_order(test_db: Session, investigator):
    """Verify investigation of existing seeded order."""
    seed_database(test_db)
    payload = OrderInvestigationInput(order_number="ORD-2026-001")
    result = investigator.investigate(test_db, payload)

    assert result.order_exists is True
    assert result.order_number == "ORD-2026-001"
    assert result.order_details is not None
    assert result.order_details.product_name == "Ergonomic Office Chair"
    assert result.order_details.delivery_status == "delivered"
    assert result.refund_status == "not_recorded"
    assert "delivered at" in result.delivery_summary.lower()


def test_investigate_unknown_order(test_db: Session, investigator):
    """Verify investigation handles unknown order correctly."""
    seed_database(test_db)
    payload = OrderInvestigationInput(order_number="ORD-NONEXISTENT-999")
    result = investigator.investigate(test_db, payload)

    assert result.order_exists is False
    assert result.order_details is None
    assert "not found" in result.delivery_summary.lower()
    assert len(result.missing_information) > 0


def test_investigate_customer_with_previous_cases(test_db: Session, investigator):
    """Verify historical complaints are retrieved for customer with prior cases."""
    seed_database(test_db)
    # Alice Chen (customer 1) has case CASE-2026-1001
    payload = OrderInvestigationInput(order_number="ORD-2026-002")
    result = investigator.investigate(test_db, payload)

    assert result.order_exists is True
    assert len(result.previous_cases) >= 1
    assert any(c.case_number == "CASE-2026-1001" for c in result.previous_cases)


def test_investigate_customer_with_no_previous_cases(test_db: Session, investigator):
    """Verify customer without prior cases returns empty previous_cases list."""
    # Create isolated customer with order but no cases
    now = utc_now()
    cust = Customer(name="No Case Cust", email="nocase@example.com", created_at=now)
    test_db.add(cust)
    test_db.flush()

    order = Order(
        order_number="ORD-NOCASE-01",
        customer_id=cust.id,
        product_name="Sample Standalone Item",
        order_status="delivered",
        delivery_status="delivered",
        order_date=now,
        expected_delivery_date=now,
        delivered_at=now,
        total_amount=500000,
        currency="INR",
        created_at=now,
    )
    test_db.add(order)
    test_db.commit()

    payload = OrderInvestigationInput(order_number="ORD-NOCASE-01")
    result = investigator.investigate(test_db, payload)

    assert result.order_exists is True
    assert len(result.previous_cases) == 0


def test_investigate_via_case_number(test_db: Session, investigator):
    """Verify investigation locates order when only case_number is provided."""
    seed_database(test_db)
    payload = OrderInvestigationInput(case_number="CASE-2026-1002")
    result = investigator.investigate(test_db, payload)

    assert result.order_exists is True
    assert result.order_number == "ORD-2026-003"
    assert result.order_details.product_name == "Ultra-HD 27-inch Monitor"
