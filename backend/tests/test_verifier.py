import pytest
from app.agents.verifier import VerifierAgent
from app.schemas.agent_schemas import (
    OrderDetailsSchema,
    OrderInvestigationResult,
    PolicyRetrievalResult,
    ResolutionRecommendationResult,
    VerificationInput,
)


@pytest.fixture
def verifier():
    return VerifierAgent()


def test_verify_valid_recommendation(verifier):
    """Verify clean recommendation passes verification."""
    rec = ResolutionRecommendationResult(
        recommendation_type="recommend_replacement_review",
        title="Recommend Replacement Review",
        reasoning="Customer received broken unit within 30-day window under ₹5,000.",
        action_required="Submit replacement request for approval.",
        human_approval_required=False,
    )
    oi = OrderInvestigationResult(
        order_exists=True,
        order_number="ORD-2026-005",
        order_details=OrderDetailsSchema(
            id=5,
            order_number="ORD-2026-005",
            product_name="Dock",
            order_status="delivered",
            delivery_status="delivered",
            total_amount=499900,
            currency="INR",
            customer_id=3,
        ),
        limitations="None",
    )
    pe = PolicyRetrievalResult(
        query="damaged",
        found_relevant=True,
        explanation="Direct policy match",
    )

    inp = VerificationInput(recommendation=rec, order_investigation=oi, policy_evidence=pe)
    result = verifier.verify(inp)

    assert result.is_valid is True
    assert result.verification_status == "pass"
    assert len(result.detected_issues) == 0


def test_verify_detects_false_completion_claim(verifier):
    """Verify verifier flags claims that a refund was already issued/completed."""
    rec = ResolutionRecommendationResult(
        recommendation_type="recommend_refund_review",
        title="Refund Issued",
        reasoning="The refund was processed and money was returned to customer credit card.",
        action_required="Close ticket.",
    )
    inp = VerificationInput(recommendation=rec)
    result = verifier.verify(inp)

    assert result.is_valid is False
    assert result.verification_status == "fail"
    assert any("completed" in issue.lower() for issue in result.detected_issues)


def test_verify_detects_order_contradiction(verifier):
    """Verify verifier flags recommendations contradicting stored order status."""
    rec = ResolutionRecommendationResult(
        recommendation_type="explain_order_status",
        title="Delivery Status",
        reasoning="Item has not yet shipped from fulfillment center.",
        action_required="Wait for shipping update.",
    )
    oi = OrderInvestigationResult(
        order_exists=True,
        order_number="ORD-2026-001",
        order_details=OrderDetailsSchema(
            id=1,
            order_number="ORD-2026-001",
            product_name="Chair",
            order_status="delivered",
            delivery_status="delivered",
            total_amount=1999900,
            currency="INR",
            customer_id=1,
        ),
        limitations="None",
    )
    inp = VerificationInput(recommendation=rec, order_investigation=oi)
    result = verifier.verify(inp)

    assert result.is_valid is False
    assert result.verification_status == "fail"
    assert any("contradicts" in issue.lower() for issue in result.detected_issues)


def test_verify_detects_unsupported_policy_citation(verifier):
    """Verify verifier flags asserting policy authorization when no policy evidence was found."""
    rec = ResolutionRecommendationResult(
        recommendation_type="recommend_refund_review",
        title="Policy Refund",
        reasoning="According to policy, the customer is entitled to immediate cash reimbursement.",
        action_required="Process refund.",
    )
    pe = PolicyRetrievalResult(
        query="unsupported",
        found_relevant=False,
        explanation="No matching policy found",
    )
    inp = VerificationInput(recommendation=rec, policy_evidence=pe)
    result = verifier.verify(inp)

    assert result.is_valid is False
    assert result.verification_status == "fail"
    assert any("cites policy" in issue.lower() for issue in result.detected_issues)
