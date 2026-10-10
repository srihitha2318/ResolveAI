from typing import List
from app.core.llm_provider import get_llm_provider
from app.core.policy_rules import (
    TIER_1_MAX_AMOUNT_PAISE,
    HIGH_VALUE_THRESHOLD_PAISE,
    format_inr,
    resolve_policy_precedence,
)
from app.schemas.agent_schemas import (
    ResolutionRecommendationInput,
    ResolutionRecommendationResult,
)


class ResolutionRecommenderAgent:
    """
    Agent responsible for synthesizing complaint analysis, verified order facts,
    and retrieved policy evidence into an actionable resolution recommendation.
    Keeps recommendations strictly separate from action execution and adheres
    to Indian marketplace standards (INR / paise).
    """

    def __init__(self):
        self.llm = get_llm_provider()

    def recommend(self, input_data: ResolutionRecommendationInput) -> ResolutionRecommendationResult:
        """Generates evidence-backed resolution recommendation using rule-based reasoning."""
        ca = input_data.complaint_analysis
        oi = input_data.order_investigation
        pe = input_data.policy_evidence

        missing_info: List[str] = []
        evidence_used: List[str] = []

        # 1. Missing Order or Information Scenario
        if not oi.order_exists:
            missing_info.append("Valid order confirmation")
            if oi.order_number:
                missing_info.append(f"Matching database entry for {oi.order_number}")
            return ResolutionRecommendationResult(
                recommendation_type="request_more_info",
                title="Request Verified Order Details from Customer",
                reasoning=(
                    f"Customer reported issue '{ca.main_issue}', but order "
                    f"'{oi.order_number or 'unspecified'}' could not be verified in the order records."
                ),
                action_required="Contact customer to verify order number and registered email address or phone number.",
                human_approval_required=False,
                missing_information=missing_info,
                evidence_used=[f"Complaint Category: {ca.category}"],
                method="rule_based",
            )

        order_details = oi.order_details
        formatted_total = order_details.total_amount_formatted or format_inr(order_details.total_amount)
        evidence_used.append(f"Order #{order_details.order_number}: Status='{order_details.order_status}', Delivery='{order_details.delivery_status}'")
        evidence_used.append(f"Total Amount: {formatted_total} ({order_details.currency})")

        if order_details.seller_id:
            evidence_used.append(f"Seller: {order_details.seller_id}")
        if order_details.category:
            evidence_used.append(f"Category: {order_details.category}")

        if pe.found_relevant:
            for p in pe.passages[:2]:
                doc_lbl = f"[{p.document_name}]"
                if p.policy_id:
                    doc_lbl = f"[{p.policy_id} {p.document_name}]"
                evidence_used.append(f"Policy {doc_lbl}: {p.passage[:100]}...")
        else:
            missing_info.append("Relevant policy passage")

        is_tier2 = order_details.total_amount > TIER_1_MAX_AMOUNT_PAISE
        is_high_value = order_details.total_amount > HIGH_VALUE_THRESHOLD_PAISE

        # 2. Damaged Product Scenario
        if ca.category == "damaged_product":
            if not pe.found_relevant:
                return ResolutionRecommendationResult(
                    recommendation_type="escalate_to_human",
                    title="Escalate Damaged Product Claim for Manual Policy Review",
                    reasoning="Customer reported damaged item, but no matching damaged-goods return policy was retrieved.",
                    action_required="Support supervisor must review damage claim manually.",
                    human_approval_required=True,
                    missing_information=["Verified return/damage policy"],
                    evidence_used=evidence_used,
                    method="rule_based",
                )

            tier_desc = (
                f"Within Tier 1 automated threshold ({format_inr(TIER_1_MAX_AMOUNT_PAISE)})."
                if not is_tier2
                else f"Exceeds Tier 1 threshold ({format_inr(TIER_1_MAX_AMOUNT_PAISE)}), requiring Tier 2 supervisor approval."
            )
            if is_high_value:
                tier_desc = f"Classified as high-value (> {format_inr(HIGH_VALUE_THRESHOLD_PAISE)}), requiring senior supervisor co-authorization."

            return ResolutionRecommendationResult(
                recommendation_type="recommend_replacement_review" if not is_tier2 else "escalate_to_human",
                title="Recommend Replacement Under Damage Policy" if not is_tier2 else "Escalate High-Value Damage Claim to Supervisor",
                reasoning=(
                    f"Customer reported damaged product ({order_details.product_name}). "
                    f"Order total is {formatted_total}. {tier_desc}"
                ),
                action_required="Review uploaded photo/unboxing evidence and create replacement approval request.",
                human_approval_required=is_tier2,
                missing_information=["Verified photograph/video of damaged item"] if ca.image_relevant else [],
                evidence_used=evidence_used,
                method="rule_based",
            )

        # 3. Refund Request Scenario
        if ca.category == "refund_request":
            tier_desc = (
                f"Order amount {formatted_total} is within standard Tier 1 threshold ({format_inr(TIER_1_MAX_AMOUNT_PAISE)})."
                if not is_tier2
                else f"Order amount {formatted_total} exceeds Tier 1 threshold ({format_inr(TIER_1_MAX_AMOUNT_PAISE)}), requiring supervisor sign-off."
            )

            return ResolutionRecommendationResult(
                recommendation_type="recommend_refund_review",
                title="Recommend Refund Evaluation" if not is_tier2 else "Recommend Refund with Supervisor Review",
                reasoning=(
                    f"Customer requested refund for {order_details.product_name}. "
                    f"Current delivery status is '{order_details.delivery_status}'. {tier_desc}"
                ),
                action_required="Submit refund approval request for financial review (no funds disbursed yet).",
                human_approval_required=is_tier2,
                missing_information=["Confirmed item return receipt or defect diagnostics"],
                evidence_used=evidence_used,
                method="rule_based",
            )

        # 4. Delayed Delivery Scenario
        if ca.category in ("delayed_delivery", "missing_order"):
            return ResolutionRecommendationResult(
                recommendation_type="explain_order_status",
                title="Provide Tracking Details & Initiate Carrier Status Check",
                reasoning=(
                    f"Customer inquired about delayed/missing shipment. Stored order status is "
                    f"'{order_details.order_status}' with delivery status '{order_details.delivery_status}'."
                ),
                action_required="Send current carrier hub tracking status to customer and monitor transit updates.",
                human_approval_required=False,
                missing_information=[],
                evidence_used=evidence_used,
                method="rule_based",
            )

        # 5. General or Other Scenario
        return ResolutionRecommendationResult(
            recommendation_type="request_more_info",
            title="Request Additional Context on Customer Inquiry",
            reasoning=f"Customer issue '{ca.main_issue}' requires additional diagnostic clarification.",
            action_required="Reply to customer requesting specific details regarding their concern.",
            human_approval_required=False,
            missing_information=["Specific resolution desired"],
            evidence_used=evidence_used,
            method="rule_based",
        )
