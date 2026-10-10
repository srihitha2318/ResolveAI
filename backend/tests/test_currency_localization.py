import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.policy_rules import (
    CURRENCY_CODE,
    CURRENCY_SYMBOL,
    TIER_1_MAX_AMOUNT_PAISE,
    HIGH_VALUE_THRESHOLD_PAISE,
    format_inr,
)
from app.database.models import Order
from app.database.seed import seed_database
from app.schemas.agent_schemas import OrderDetailsSchema


def test_currency_constants():
    """Verify system-wide currency constants are set to INR and ₹."""
    assert CURRENCY_CODE == "INR"
    assert CURRENCY_SYMBOL == "₹"
    assert TIER_1_MAX_AMOUNT_PAISE == 500000  # ₹5,000.00 in integer paise
    assert HIGH_VALUE_THRESHOLD_PAISE == 2500000  # ₹25,000.00 in integer paise


def test_format_inr_indian_number_grouping():
    """Verify format_inr correctly formats amounts with Indian comma grouping."""
    assert format_inr(149900) == "₹1,499.00"
    assert format_inr(1899900) == "₹18,999.00"
    assert format_inr(5499000) == "₹54,990.00"
    assert format_inr(14999900) == "₹1,49,999.00"
    assert format_inr(0) == "₹0.00"
    assert format_inr(50) == "₹0.50"
    assert format_inr(99) == "₹0.99"
    assert format_inr(100) == "₹1.00"
    assert format_inr(10000000) == "₹1,00,000.00"  # 1 Lakh INR
    assert format_inr(1000000000) == "₹1,00,00,000.00"  # 1 Crore INR


def test_format_inr_negative():
    """Verify negative amounts format correctly with minus sign and symbol."""
    assert format_inr(-149900) == "-₹1,499.00"


def test_database_orders_inr_paise(test_db: Session):
    """Verify all database orders use INR and integer paise."""
    seed_database(test_db)
    orders = test_db.execute(select(Order)).scalars().all()
    assert len(orders) > 0
    for order in orders:
        assert order.currency == "INR", f"Order {order.order_number} has currency {order.currency}"
        assert isinstance(order.total_amount, int), f"Order {order.order_number} amount is not integer"
        # All realistic seed orders have amount > ₹100 (10,000 paise)
        assert order.total_amount >= 10000, f"Order {order.order_number} amount {order.total_amount} too low for paise"


def test_schema_documentation_mentions_paise():
    """Verify OrderDetailsSchema explicitly documents total_amount in paise."""
    schema = OrderDetailsSchema.model_json_schema()
    props = schema.get("properties", {})
    total_amount_prop = props.get("total_amount", {})
    description = total_amount_prop.get("description", "").lower()
    assert "paise" in description
    assert "inr" in description
