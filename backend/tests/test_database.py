from datetime import datetime, timezone
import pytest
from sqlalchemy import select, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.init_db import init_db
from app.database.models import (
    Customer,
    Order,
    SupportCase,
    SupportTicket,
    CustomerFeedback,
    utc_now,
)


def test_database_tables_exist(test_engine):
    """Verify all 8 required tables exist in the schema."""
    inspector = inspect(test_engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "customers",
        "orders",
        "support_cases",
        "support_tickets",
        "approval_requests",
        "case_events",
        "call_summaries",
        "customer_feedback",
    }
    assert expected_tables.issubset(table_names)


def test_idempotent_init_db(test_engine, test_db: Session):
    """Verify init_db can be called multiple times without error or data loss."""
    # Insert a customer
    cust = Customer(name="Test User", email="test.user@example.com")
    test_db.add(cust)
    test_db.commit()

    # Call init_db again
    init_db(test_engine)

    # Check record is still present
    queried = test_db.execute(
        select(Customer).where(Customer.email == "test.user@example.com")
    ).scalar_one_or_none()
    assert queried is not None
    assert queried.name == "Test User"


def test_foreign_key_enforcement(test_db: Session):
    """Verify SQLite foreign key enforcement rejects orphaned records."""
    now = utc_now()
    # Attempt to insert an order with non-existent customer_id = 99999
    orphan_order = Order(
        order_number="ORD-INVALID-999",
        customer_id=99999,
        product_name="Ghost Item",
        order_status="pending",
        delivery_status="not_shipped",
        order_date=now,
        expected_delivery_date=now,
        total_amount=1000,
        currency="INR",
    )
    test_db.add(orphan_order)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_unique_order_number_constraint(test_db: Session):
    """Verify order_number uniqueness is enforced."""
    now = utc_now()
    cust = Customer(name="Customer Unique", email="unique@example.com")
    test_db.add(cust)
    test_db.flush()

    order1 = Order(
        order_number="ORD-UNIQUE-1",
        customer_id=cust.id,
        product_name="Product 1",
        order_status="shipped",
        delivery_status="in_transit",
        order_date=now,
        expected_delivery_date=now,
        total_amount=2500,
        currency="INR",
    )
    test_db.add(order1)
    test_db.commit()

    order2 = Order(
        order_number="ORD-UNIQUE-1",  # duplicate order number
        customer_id=cust.id,
        product_name="Product 2",
        order_status="shipped",
        delivery_status="in_transit",
        order_date=now,
        expected_delivery_date=now,
        total_amount=3500,
        currency="INR",
    )
    test_db.add(order2)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_rating_check_constraint(test_db: Session):
    """Verify rating outside 1-5 raises an integrity error."""
    cust = Customer(name="Feedback User", email="feedback@example.com")
    test_db.add(cust)
    test_db.flush()

    case = SupportCase(
        case_number="CASE-FEEDBACK-01",
        customer_id=cust.id,
        subject="Feedback test",
        complaint_text="Testing rating bounds",
        status="closed",
        priority="low",
    )
    test_db.add(case)
    test_db.flush()

    invalid_feedback = CustomerFeedback(
        case_id=case.id,
        rating=10,  # Invalid: check constraint requires 1 <= rating <= 5
        comments="Out of range rating",
    )
    test_db.add(invalid_feedback)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()
