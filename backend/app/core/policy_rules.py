"""
Centralized business rules, policy precedence definitions, and Indian Currency (INR) utilities
for the ResolveAI Indian e-commerce marketplace platform.
"""

from typing import Any, Dict, List, Optional, Tuple


# Currency standard constants
CURRENCY_CODE = "INR"
CURRENCY_SYMBOL = "₹"

# Centralized financial thresholds in paise (1 INR = 100 paise)
# Tier 1 automated review limit: ₹5,000.00 (5,00,000 paise)
TIER_1_MAX_AMOUNT_PAISE = 500_000

# High-value order threshold requiring supervisor sign-off: ₹25,000.00 (25,00,000 paise)
HIGH_VALUE_THRESHOLD_PAISE = 2_500_000

# Standard return window defaults (in calendar days)
DEFAULT_RETURN_WINDOW_DAYS = 30
CATEGORY_RETURN_WINDOWS = {
    "electronics": 7,          # 7-day replacement for defective/damaged electronics
    "fashion": 14,              # 14-day return/exchange with tags and hygiene seals intact
    "home_appliances": 10,      # 10-day replacement upon technician inspection
    "general_merchandise": 7,   # 7-day standard return window for non-appliance goods
}

# Precedence levels (lower number indicates higher authority)
PRECEDENCE_PLATFORM_SECURITY = 1  # Non-overridable security & anti-fraud controls
PRECEDENCE_PLATFORM_POLICY = 2    # Platform-wide support, return & refund rules
PRECEDENCE_CATEGORY_POLICY = 3    # Category-specific technical & return rules
PRECEDENCE_SELLER_POLICY = 4      # Seller-specific rules (only where permitted by platform)


def format_inr(paise: int) -> str:
    """
    Formats monetary amount stored in integer paise using standard Indian number grouping.
    Example:
        149900 -> '₹1,499.00'
        1899900 -> '₹18,999.00'
        14999900 -> '₹1,49,999.00'
        5499000 -> '₹54,990.00'
        0 -> '₹0.00'
    """
    if paise is None:
        return f"{CURRENCY_SYMBOL}0.00"

    is_negative = paise < 0
    abs_paise = abs(paise)

    rupees = abs_paise // 100
    rem_paise = abs_paise % 100

    rupees_str = str(rupees)

    # Indian number grouping: last 3 digits, then groups of 2 digits
    if len(rupees_str) <= 3:
        formatted_rupees = rupees_str
    else:
        last_three = rupees_str[-3:]
        remaining = rupees_str[:-3]
        # Group remaining digits in pairs of 2 from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_rupees = ",".join(groups) + "," + last_three

    result = f"{CURRENCY_SYMBOL}{formatted_rupees}.{rem_paise:02d}"
    return f"-{result}" if is_negative else result


def paise_to_rupees(paise: int) -> float:
    """Converts integer paise to float rupees for display purposes only."""
    return round((paise or 0) / 100.0, 2)


def rupees_to_paise(rupees: float | int) -> int:
    """Converts rupee amount to integer paise, avoiding floating point inaccuracies."""
    return int(round(float(rupees) * 100))


POLICY_SCOPES = ["platform_constraint", "platform", "category", "seller"]
PREFERENCE_HIERARCHY = {
    "platform_constraint": 1,
    "platform": 2,
    "category": 3,
    "seller": 4,
}


def resolve_policy_precedence(
    policies: Optional[List[Dict[str, Any]]] = None,
    order_category: Optional[str] = None,
    order_seller_id: Optional[str] = None,
    has_direct_conflict: bool = False,
    platform_rule: Optional[Dict[str, Any]] = None,
    category_rule: Optional[Dict[str, Any]] = None,
    seller_rule: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Resolves policy precedence across platform constraints, platform-wide,
    category-specific, and seller-specific policies.

    Hierarchy:
    1. Platform non-overridable constraints (security, fraud prevention, audit controls)
    2. Applicable platform-wide policy
    3. Applicable category-specific policy
    4. Applicable seller-specific policy (only where permitted by platform)

    Returns a dict with:
        status: 'resolved' or 'needs_review'
        winning_policy: Dict or None
        rule: str or None
        explanation: str
        conflicting_policy_ids: List[str]
        requires_human_review: bool
    """
    # If passed separate rules, build policy list
    policy_list: List[Dict[str, Any]] = []
    if policies is not None:
        policy_list = list(policies)
    else:
        if platform_rule:
            p_rule = dict(platform_rule)
            p_rule.setdefault("scope", "platform_constraint" if p_rule.get("is_mandatory_constraint") else "platform")
            policy_list.append(p_rule)
        if category_rule:
            c_rule = dict(category_rule)
            c_rule.setdefault("scope", "category")
            policy_list.append(c_rule)
        if seller_rule:
            s_rule = dict(seller_rule)
            s_rule.setdefault("scope", "seller")
            policy_list.append(s_rule)

    if not policy_list:
        return {
            "status": "needs_review",
            "winning_policy": None,
            "rule": "No matching policy rule found.",
            "explanation": "No applicable policy rules supplied. Requires human review.",
            "conflicting_policy_ids": [],
            "requires_human_review": True,
        }

    # If explicit conflict flag is passed or identical scopes with conflicting terms
    if has_direct_conflict:
        conflicting_ids = [p.get("policy_id", "UNKNOWN") for p in policy_list]
        return {
            "status": "needs_review",
            "winning_policy": None,
            "rule": None,
            "explanation": f"Direct policy conflict between policies: {', '.join(conflicting_ids)}. Case flagged for human supervisor review.",
            "conflicting_policy_ids": conflicting_ids,
            "requires_human_review": True,
        }

    # Filter applicable policies
    applicable = []
    for p in policy_list:
        scope = p.get("scope", "platform")
        if scope == "category":
            p_cat = p.get("category")
            if p_cat and order_category and p_cat.lower() != order_category.lower():
                continue
        elif scope == "seller":
            p_sel = p.get("seller_id")
            if p_sel and order_seller_id:
                norm_p = p_sel.replace("SLR-", "SELLER-") if p_sel.startswith("SLR-") else p_sel
                norm_o = order_seller_id.replace("SLR-", "SELLER-") if order_seller_id.startswith("SLR-") else order_seller_id
                if norm_p != norm_o:
                    continue
        applicable.append(p)

    if not applicable:
        return {
            "status": "needs_review",
            "winning_policy": None,
            "rule": None,
            "explanation": "None of the candidate policies match the order's category or seller. Requires supervisor review.",
            "conflicting_policy_ids": [p.get("policy_id", "UNKNOWN") for p in policy_list],
            "requires_human_review": True,
        }

    # Sort by precedence: lower number = higher precedence
    applicable.sort(key=lambda x: PREFERENCE_HIERARCHY.get(x.get("scope"), 99))
    top = applicable[0]
    top_scope = top.get("scope", "platform")

    if top_scope == "platform_constraint":
        explanation = f"Non-overridable platform constraint [{top.get('policy_id')}] supersedes lower-level rules."
    elif top_scope == "platform":
        explanation = f"Platform-wide policy [{top.get('policy_id')}] applied."
    elif top_scope == "category":
        explanation = f"Category-specific policy [{top.get('policy_id')}] applied for category '{top.get('category')}'."
    elif top_scope == "seller":
        explanation = f"Seller-specific policy [{top.get('policy_id')}] applied for seller '{top.get('seller_id')}'."
    else:
        explanation = f"Policy [{top.get('policy_id')}] applied."

    return {
        "status": "resolved",
        "winning_policy": top,
        "rule": top.get("rule", ""),
        "explanation": explanation,
        "conflicting_policy_ids": [],
        "requires_human_review": False,
    }
