import pytest
from app.core.policy_rules import (
    resolve_policy_precedence,
    POLICY_SCOPES,
    PREFERENCE_HIERARCHY,
    CATEGORY_RETURN_WINDOWS,
)


def test_precedence_hierarchy_order():
    """Verify PREFERENCE_HIERARCHY is strictly ordered from constraint down to seller."""
    assert PREFERENCE_HIERARCHY["platform_constraint"] < PREFERENCE_HIERARCHY["platform"]
    assert PREFERENCE_HIERARCHY["platform"] < PREFERENCE_HIERARCHY["category"]
    assert PREFERENCE_HIERARCHY["category"] < PREFERENCE_HIERARCHY["seller"]


def test_platform_constraint_cannot_be_overridden_by_seller():
    """Verify platform constraint takes absolute precedence over seller policy."""
    policies = [
        {
            "policy_id": "POL-PLAT-005",
            "scope": "platform_constraint",
            "title": "Platform Security and Fraud Constraint",
            "rule": "Monetary refunds require mandatory human review if over ₹5,000.",
        },
        {
            "policy_id": "POL-SEL-001",
            "scope": "seller",
            "seller_id": "SELLER-001",
            "title": "Deccan Digital Seller Policy",
            "rule": "Seller may issue instant refund up to ₹10,000 without human review.",
        },
    ]

    result = resolve_policy_precedence(
        policies=policies,
        order_category="electronics",
        order_seller_id="SELLER-001",
    )

    assert result["status"] == "resolved"
    assert result["winning_policy"]["policy_id"] == "POL-PLAT-005"
    assert "platform constraint" in result["explanation"].lower()


def test_category_policy_filtered_by_category():
    """Verify category policy is ignored if order category doesn't match."""
    policies = [
        {
            "policy_id": "POL-CAT-002",
            "scope": "category",
            "category": "fashion",
            "title": "Fashion Category Policy",
            "rule": "14-day exchange window for apparel size mismatches.",
        },
        {
            "policy_id": "POL-PLAT-002",
            "scope": "platform",
            "title": "Platform Return Policy",
            "rule": "Default 7-day return window for merchandise.",
        },
    ]

    # Order is electronics, so fashion category policy does not apply
    result = resolve_policy_precedence(
        policies=policies,
        order_category="electronics",
        order_seller_id="SELLER-001",
    )

    assert result["status"] == "resolved"
    assert result["winning_policy"]["policy_id"] == "POL-PLAT-002"


def test_seller_policy_filtered_by_seller():
    """Verify seller policy is ignored if order seller_id does not match."""
    policies = [
        {
            "policy_id": "POL-SEL-002",
            "scope": "seller",
            "seller_id": "SELLER-002",
            "title": "VastraKart Seller Policy",
            "rule": "Free dry-cleaning replacement within 10 days.",
        },
        {
            "policy_id": "POL-PLAT-002",
            "scope": "platform",
            "title": "Platform Return Policy",
            "rule": "Standard platform return guidelines.",
        },
    ]

    # Order is from SELLER-001, so SELLER-002 policy does not apply
    result = resolve_policy_precedence(
        policies=policies,
        order_category="fashion",
        order_seller_id="SELLER-001",
    )

    assert result["status"] == "resolved"
    assert result["winning_policy"]["policy_id"] == "POL-PLAT-002"


def test_unresolvable_conflict_returns_needs_review():
    """Verify two conflicting policies at the same precedence level return needs_review."""
    policies = [
        {
            "policy_id": "POL-SEL-001A",
            "scope": "seller",
            "seller_id": "SELLER-001",
            "title": "Deccan Digital Variant A",
            "rule": "Replacement must be issued within 48 hours without technician visit.",
        },
        {
            "policy_id": "POL-SEL-001B",
            "scope": "seller",
            "seller_id": "SELLER-001",
            "title": "Deccan Digital Variant B",
            "rule": "Replacement strictly requires authorized technician inspection report.",
        },
    ]

    result = resolve_policy_precedence(
        policies=policies,
        order_category="electronics",
        order_seller_id="SELLER-001",
        has_direct_conflict=True,
    )

    assert result["status"] == "needs_review"
    assert result["winning_policy"] is None
    assert "POL-SEL-001A" in result["conflicting_policy_ids"]
    assert "POL-SEL-001B" in result["conflicting_policy_ids"]
    assert len(result["conflicting_policy_ids"]) == 2


def test_category_return_windows():
    """Verify category return windows are correctly configured."""
    assert CATEGORY_RETURN_WINDOWS["electronics"] == 7
    assert CATEGORY_RETURN_WINDOWS["fashion"] == 14
    assert CATEGORY_RETURN_WINDOWS["home_appliances"] == 10
    assert CATEGORY_RETURN_WINDOWS["general_merchandise"] == 7
