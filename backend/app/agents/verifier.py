import re
from typing import List
from app.schemas.agent_schemas import (
    VerificationInput,
    VerificationResult,
)


class VerifierAgent:
    """
    Agent responsible for independently checking proposed resolution recommendations
    against underlying facts, order states, policy citations, and execution boundaries.
    """

    def verify(self, input_data: VerificationInput) -> VerificationResult:
        """Executes factual consistency and integrity verification."""
        rec = input_data.recommendation
        oi = input_data.order_investigation
        pe = input_data.policy_evidence

        detected_issues: List[str] = []
        evidence_checked: List[str] = []
        missing_evidence: List[str] = []

        # 1. Check order existence and facts
        if oi:
            evidence_checked.append("Order investigation existence and status")
            if not oi.order_exists and rec.recommendation_type not in ("request_more_info", "insufficient_evidence"):
                detected_issues.append(
                    f"Recommendation recommends '{rec.recommendation_type}' but order '{oi.order_number}' does not exist in the database."
                )

            # Check for contradiction with stored order status
            if oi.order_exists and oi.order_details:
                od = oi.order_details
                if od.delivery_status == "delivered" and "Item has not yet shipped" in rec.reasoning:
                    detected_issues.append("Recommendation contradicts stored delivery status: order is already delivered.")
                if od.order_status == "cancelled" and rec.recommendation_type == "explain_order_status" and "in transit" in rec.reasoning:
                    detected_issues.append("Recommendation contradicts stored order status: order is cancelled.")

        # 2. Check for false claims of completed actions
        # Look for past tense claims implying execution has occurred
        completion_patterns = [
            r"\brefund (?:was|has been) (?:processed|issued|completed|sent)\b",
            r"\bmoney (?:was|has been) returned\b",
            r"\breplacement (?:was|has been) (?:dispatched|shipped|created)\b",
            r"\bticket (?:was|has been) created\b",
        ]
        combined_text = f"{rec.title} {rec.reasoning} {rec.action_required}".lower()
        for pat in completion_patterns:
            if re.search(pat, combined_text):
                detected_issues.append(
                    f"Recommendation claims a finalized action has been completed ('{pat}'), "
                    "violating Level 2 boundary (recommendations must not claim execution without confirmation)."
                )

        # 3. Check policy evidence citations
        if pe:
            evidence_checked.append("Policy retrieval evidence")
            if not pe.found_relevant and "policy" in rec.reasoning.lower():
                # If recommendation specifically asserts policy authorization despite no found policy
                if "according to policy" in rec.reasoning.lower() or "policy allows" in rec.reasoning.lower():
                    detected_issues.append(
                        "Recommendation cites policy authorization, but policy retriever found no matching policy passages."
                    )
                    missing_evidence.append("Valid policy citation")

        # 4. Check missing information
        if rec.missing_information:
            missing_evidence.extend(rec.missing_information)

        # 5. Check human approval consistency
        if rec.human_approval_required and not detected_issues:
            evidence_checked.append("Human supervisor approval required flag")

        # Determine pass/fail
        is_valid = len(detected_issues) == 0
        verification_status = "pass" if is_valid else "fail"

        if is_valid:
            if rec.human_approval_required:
                next_step = "Submit recommendation to supervisor queue for human review and approval."
            else:
                next_step = "Proceed with recommended response to customer."
        else:
            next_step = f"Halt resolution. Address {len(detected_issues)} factual or policy discrepancies before continuing."

        return VerificationResult(
            verification_status=verification_status,
            is_valid=is_valid,
            detected_issues=detected_issues,
            evidence_checked=evidence_checked,
            missing_evidence=missing_evidence,
            required_next_step=next_step,
        )
