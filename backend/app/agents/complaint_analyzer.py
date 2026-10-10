import re
from typing import Optional
from app.core.llm_provider import get_llm_provider
from app.core.logging_config import logger
from app.schemas.agent_schemas import ComplaintAnalysisInput, ComplaintAnalysisResult


class ComplaintAnalyzerAgent:
    """
    Agent responsible for analyzing incoming customer complaint text,
    extracting key issues, identifying desired outcomes, and classifying categories.
    """

    SUPPORTED_CATEGORIES = [
        "delayed_delivery",
        "missing_order",
        "damaged_product",
        "refund_request",
        "replacement_request",
        "wrong_item",
        "cancellation",
        "warranty",
        "other",
    ]

    def __init__(self):
        self.llm = get_llm_provider()

    def analyze(self, input_data: ComplaintAnalysisInput) -> ComplaintAnalysisResult:
        """Executes complaint analysis using LLM if available or robust rule-based parsing."""
        raw_text = (input_data.complaint_text or "").strip()
        extracted_order = input_data.order_number

        # Check for order number pattern in text if not explicitly provided
        if not extracted_order and raw_text:
            match = re.search(r"\b(ORD-[A-Za-z0-9\-]+)\b", raw_text, re.IGNORECASE)
            if match:
                extracted_order = match.group(1).upper()

        if not raw_text:
            return ComplaintAnalysisResult(
                category="other",
                main_issue="No complaint text provided.",
                desired_outcome=None,
                order_number=extracted_order,
                image_relevant=False,
                additional_info_required=True,
                analysis_method="rule_based",
                limitations="Input text was empty; cannot determine customer concern without content.",
            )

        # Rule-based deterministic classification
        return self._rule_based_analysis(raw_text, extracted_order)

    def _rule_based_analysis(self, text: str, order_number: Optional[str]) -> ComplaintAnalysisResult:
        t_lower = text.lower()

        category = "other"
        image_relevant = False
        desired_outcome = None
        additional_info_required = False

        # Category prioritization
        if any(w in t_lower for w in ["damaged", "broken", "bent", "defect", "cracked", "shattered", "scratched"]):
            category = "damaged_product"
            image_relevant = True
            desired_outcome = "Replacement or compensation for damaged item"
        elif any(w in t_lower for w in ["wrong item", "different product", "wrong product", "incorrect item", "received wrong"]):
            category = "wrong_item"
            image_relevant = True
            desired_outcome = "Correct item dispatched or return initiated"
        elif any(w in t_lower for w in ["refund", "money back", "reimburse", "return payment"]):
            category = "refund_request"
            desired_outcome = "Full or partial monetary refund"
        elif any(w in t_lower for w in ["replacement", "replace", "send another", "exchange"]):
            category = "replacement_request"
            desired_outcome = "Replacement unit shipped"
        elif any(w in t_lower for w in ["cancel", "cancellation", "stop order", "don't want anymore"]):
            category = "cancellation"
            desired_outcome = "Order cancellation and charge reversal"
        elif any(w in t_lower for w in ["never arrived", "lost", "missing order", "didn't receive", "not received"]):
            category = "missing_order"
            desired_outcome = "Package investigation or expedited reshipment"
        elif any(w in t_lower for w in ["delay", "late", "where is", "not shipped", "tracking stuck", "not delivered"]):
            category = "delayed_delivery"
            desired_outcome = "Tracking status update and delivery expedition"
        elif any(w in t_lower for w in ["warranty", "guarantee", "malfunction after"]):
            category = "warranty"
            desired_outcome = "Warranty service or replacement"

        # Determine main issue summary
        sentences = [s.strip() for s in re.split(r"[.!?\n]", text) if s.strip()]
        main_issue = sentences[0] if sentences else text[:120]

        # Additional information check
        limitations = None
        if not order_number:
            additional_info_required = True
            limitations = "No order number was provided or detected in the complaint text."

        if category == "other" and not additional_info_required:
            limitations = "Complaint topic could not be matched with high confidence to specific support category."

        return ComplaintAnalysisResult(
            category=category,
            main_issue=main_issue,
            desired_outcome=desired_outcome,
            order_number=order_number,
            image_relevant=image_relevant,
            additional_info_required=additional_info_required,
            analysis_method="rule_based",
            limitations=limitations,
        )
