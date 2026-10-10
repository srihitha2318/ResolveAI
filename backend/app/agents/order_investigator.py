from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Order
from app.core.policy_rules import format_inr
from app.schemas.agent_schemas import (
    OrderInvestigationInput,
    OrderInvestigationResult,
    OrderDetailsSchema,
    CaseSummarySchema,
)
from app.tools.support_tools import (
    get_order_details,
    get_case_details,
    get_previous_complaints,
    get_refund_status,
)


class OrderInvestigatorAgent:
    """
    Agent responsible for investigating order details, delivery status,
    historical complaints, and stored refund statuses using real database tools.
    """

    def investigate(self, db: Session, input_data: OrderInvestigationInput) -> OrderInvestigationResult:
        """Executes order investigation using actual stored database records."""
        order_num = input_data.order_number

        # If order number is not provided but case number is, look up the order via case
        if not order_num and input_data.case_number:
            case_data = get_case_details(db, input_data.case_number)
            if case_data and case_data.get("order_id"):
                ord_obj = db.execute(
                    select(Order).where(Order.id == case_data["order_id"])
                ).scalar_one_or_none()
                if ord_obj:
                    order_num = ord_obj.order_number

        if not order_num:
            return OrderInvestigationResult(
                order_exists=False,
                order_number=None,
                order_details=None,
                delivery_summary="Cannot investigate delivery without an order number or valid case reference.",
                previous_cases=[],
                refund_status="unknown",
                missing_information=["order_number"],
                limitations="Neither an order number nor a case referencing a valid order was supplied.",
            )

        order_raw = get_order_details(db, order_num)

        if not order_raw:
            return OrderInvestigationResult(
                order_exists=False,
                order_number=order_num,
                order_details=None,
                delivery_summary=f"Order '{order_num}' was not found in database records.",
                previous_cases=[],
                refund_status="unknown",
                missing_information=[f"Valid order record for {order_num}"],
                limitations="Unable to verify shipping, payment, or delivery status for non-existent order.",
            )

        # Build OrderDetailsSchema
        order_details = OrderDetailsSchema(
            id=order_raw["id"],
            order_number=order_raw["order_number"],
            product_name=order_raw["product_name"],
            order_status=order_raw["order_status"],
            delivery_status=order_raw["delivery_status"],
            order_date=order_raw["order_date"],
            expected_delivery_date=order_raw["expected_delivery_date"],
            delivered_at=order_raw["delivered_at"],
            total_amount=order_raw["total_amount"],  # integer paise
            currency=order_raw.get("currency", "INR"),
            customer_id=order_raw["customer_id"],
            seller_id=order_raw.get("seller_id"),
            category=order_raw.get("category"),
            total_amount_formatted=order_raw.get("total_amount_formatted") or format_inr(order_raw["total_amount"]),
        )

        # Historical complaints
        prev_raw = get_previous_complaints(db, order_raw["customer_id"])
        prev_cases = [
            CaseSummarySchema(
                id=c["id"],
                case_number=c["case_number"],
                order_id=c["order_id"],
                subject=c["subject"],
                status=c["status"],
                priority=c["priority"],
                created_at=c["created_at"],
            )
            for c in prev_raw
        ]

        # Refund status
        refund_info = get_refund_status(db, order_num)
        refund_status = refund_info.get("refund_status", "not_recorded")

        # Delivery summary based strictly on confirmed records
        delivery_summary = f"Order status is '{order_raw['order_status']}', delivery status is '{order_raw['delivery_status']}'."
        if order_raw["delivery_status"] == "delivered":
            if order_raw["delivered_at"]:
                delivery_summary += f" Delivered at {order_raw['delivered_at']}."
            else:
                delivery_summary += " Marked delivered, but delivered_at timestamp is unrecorded."
        elif order_raw["delivery_status"] == "delayed":
            delivery_summary += f" Delivery delayed past expected delivery date ({order_raw['expected_delivery_date']})."
        elif order_raw["delivery_status"] == "not_shipped":
            delivery_summary += " Item has not yet been dispatched by fulfillment warehouse."

        missing_info: List[str] = []
        if order_raw["delivery_status"] == "delivered" and not order_raw["delivered_at"]:
            missing_info.append("delivered_at timestamp")

        limitations = (
            f"{refund_info.get('limitation', '')} "
            "Delivery completion is verified solely against stored delivered_at records, not carrier telemetry."
        ).strip()

        return OrderInvestigationResult(
            order_exists=True,
            order_number=order_num,
            order_details=order_details,
            delivery_summary=delivery_summary,
            previous_cases=prev_cases,
            refund_status=refund_status,
            missing_information=missing_info,
            limitations=limitations,
        )
