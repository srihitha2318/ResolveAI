from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database.seed import seed_database
from app.database.models import Customer, Order, SupportCase, SupportTicket


def test_seed_database_record_counts(test_db: Session):
    """Verify seed_database creates the required minimum synthetic records."""
    stats = seed_database(test_db)

    assert stats["customers"]["inserted"] >= 5
    assert stats["orders"]["inserted"] >= 8
    assert stats["support_cases"]["inserted"] >= 5

    # Verify actual database row counts
    cust_count = test_db.scalar(select(func.count(Customer.id)))
    order_count = test_db.scalar(select(func.count(Order.id)))
    case_count = test_db.scalar(select(func.count(SupportCase.id)))

    assert cust_count >= 5
    assert order_count >= 8
    assert case_count >= 5


def test_seed_database_idempotent(test_db: Session):
    """Verify running seed_database a second time does not duplicate records."""
    first_run = seed_database(test_db)
    initial_cust_count = test_db.scalar(select(func.count(Customer.id)))
    initial_order_count = test_db.scalar(select(func.count(Order.id)))
    initial_case_count = test_db.scalar(select(func.count(SupportCase.id)))

    # Second run
    second_run = seed_database(test_db)

    # In second run, inserted must be 0 and existing must match previously inserted count
    assert second_run["customers"]["inserted"] == 0
    assert second_run["customers"]["existing"] == first_run["customers"]["inserted"]

    assert second_run["orders"]["inserted"] == 0
    assert second_run["orders"]["existing"] == first_run["orders"]["inserted"]

    assert second_run["support_cases"]["inserted"] == 0
    assert second_run["support_cases"]["existing"] == first_run["support_cases"]["inserted"]

    # Database totals must remain unchanged
    after_cust_count = test_db.scalar(select(func.count(Customer.id)))
    after_order_count = test_db.scalar(select(func.count(Order.id)))
    after_case_count = test_db.scalar(select(func.count(SupportCase.id)))

    assert after_cust_count == initial_cust_count
    assert after_order_count == initial_order_count
    assert after_case_count == initial_case_count


def test_seed_database_foreign_keys(test_db: Session):
    """Verify all seeded orders and cases link to valid customers."""
    seed_database(test_db)

    # Every order must have an existing customer
    orders = test_db.scalars(select(Order)).all()
    for ord in orders:
        assert ord.customer is not None
        assert ord.customer.email.endswith("@example.com")

    # Every case must have an existing customer
    cases = test_db.scalars(select(SupportCase)).all()
    for case in cases:
        assert case.customer is not None
        if case.order_id:
            assert case.order is not None
