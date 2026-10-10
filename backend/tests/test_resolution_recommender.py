import pytest
from app.agents.resolution_recommender import ResolutionRecommenderAgent
from app.schemas.agent_schemas import (
    ComplaintAnalysisResult,
    OrderInvestigationResult,
    OrderDetailsSchema,
    PolicyRetrievalResult,
    PolicyPassageSchema,
    ResolutionRecommendationInput,
)


@pytest.fixture
def recommender():
    return ResolutionRecommenderAgent()


def test_recommend_damaged_product_with_policy(recommender):
    """Verify recommendation recommends replacement review when damaged product and policy exist."""
    ca = ComplaintAnalysisResult(
        category="damaged_product",
        main_issue="Port is bent and broken",
        desired_outcome="Replacement",
        order_number="ORD-2026-005",
        image_relevant=True,
        additional_info_required=False,
    )
    oi = OrderInvestigationResult(
        order_exists=True,
        order_number="ORD-2026-005",
        order_details=OrderDetailsSchema(
            id=5,
            order_number="ORD-2026-005",
            product_name="Docking Station",
            order_status="delivered",
            delivery_status="delivered",
            total_amount=499900,  # ₹4,999.00 (under ₹5,000.00 Tier 1 limit)
            currency="INR",
            customer_id=3,
        ),
        limitations="None",
    )
    pe = PolicyRetrievalResult(
        query="damaged replacement",
        passages=[
            PolicyPassageSchema(
                document_name="return_policy.md",
                passage="Products damaged during shipping or defective upon arrival are eligible for replacement.",
            )
        ],
        found_relevant=True,
        explanation="Direct policy match",
    )

    inp = ResolutionRecommendationInput(
        complaint_analysis=ca,
        order_investigation=oi,
        policy_evidence=pe,
    )
    res = recommender.recommend(inp)

    assert res.recommendation_type == "recommend_replacement_review"
    assert res.human_approval_required is False
    assert "no funds disbursed" not in res.title.lower()
    # Check that recommendation does NOT claim replacement was already completed
    assert "replacement was dispatched" not in res.action_required.lower()


def test_recommend_missing_policy_escalates(recommender):
    """Verify missing policy evidence escalates damaged product to human review."""
    ca = ComplaintAnalysisResult(
        category="damaged_product",
        main_issue="Screen cracked",
        order_number="ORD-2026-003",
    )
    oi = OrderInvestigationResult(
        order_exists=True,
        order_number="ORD-2026-003",
        order_details=OrderDetailsSchema(
            id=3,
            order_number="ORD-2026-003",
            product_name="Monitor",
            order_status="shipped",
            delivery_status="delayed",
            total_amount=3499900,
            currency="INR",
            customer_id=2,
        ),
        limitations="None",
    )
    pe = PolicyRetrievalResult(
        query="damaged",
        passages=[],
        found_relevant=False,
        explanation="No matching policy found",
    )

    inp = ResolutionRecommendationInput(
        complaint_analysis=ca,
        order_investigation=oi,
        policy_evidence=pe,
    )
    res = recommender.recommend(inp)

    assert res.recommendation_type == "escalate_to_human"
    assert res.human_approval_required is True


def test_recommend_missing_order_requests_info(recommender):
    """Verify missing order record triggers request_more_info recommendation."""
    ca = ComplaintAnalysisResult(
        category="delayed_delivery",
        main_issue="Where is my order?",
        order_number="ORD-GHOST",
    )
    oi = OrderInvestigationResult(
        order_exists=False,
        order_number="ORD-GHOST",
        limitations="Order not in system",
    )
    pe = PolicyRetrievalResult(
        query="delivery",
        found_relevant=True,
        explanation="Policy found",
    )

    inp = ResolutionRecommendationInput(
        complaint_analysis=ca,
        order_investigation=oi,
        policy_evidence=pe,
    )
    res = recommender.recommend(inp)

    assert res.recommendation_type == "request_more_info"
    assert "valid order" in res.missing_information[0].lower()
