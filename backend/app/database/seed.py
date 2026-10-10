from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path
from typing import Dict
from sqlalchemy import select
from sqlalchemy.orm import Session

_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.logging_config import logger
from app.core.policy_rules import CURRENCY_CODE, format_inr
from app.database.db import SessionLocal
from app.core.auth import hash_password
from app.database.init_db import init_db
from app.database.models import (
    Customer,
    Order,
    SupportCase,
    SupportTicket,
    ApprovalRequest,
    CaseEvent,
    CallSummary,
    CustomerFeedback,
    User,
)


def seed_database(session: Session) -> Dict[str, Dict[str, int]]:
    """
    Seeds the database with deterministic synthetic development data localized for
    the Indian e-commerce marketplace (INR currency in integer paise).
    Idempotent: checks for existing unique records before inserting, and updates
    schema attributes (seller_id, category, currency) safely if missing.
    """
    stats = {
        "customers": {"inserted": 0, "existing": 0},
        "orders": {"inserted": 0, "existing": 0},
        "support_cases": {"inserted": 0, "existing": 0},
        "support_tickets": {"inserted": 0, "existing": 0},
        "approval_requests": {"inserted": 0, "existing": 0},
        "case_events": {"inserted": 0, "existing": 0},
        "call_summaries": {"inserted": 0, "existing": 0},
        "customer_feedback": {"inserted": 0, "existing": 0},
        "users": {"inserted": 0, "existing": 0},
    }

    base_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Customers (preserved original emails for backward compatibility + Indian profiles)
    synthetic_customers = [
        {"name": "Aarav Sharma", "email": "alice.chen@example.com"},
        {"name": "Bob Martinez", "email": "bob.martinez@example.com"},
        {"name": "Clara Dupont", "email": "clara.dupont@example.com"},
        {"name": "David Kim", "email": "david.kim@example.com"},
        {"name": "Elena Rostova", "email": "elena.rostova@example.com"},
        {"name": "Priya Patel", "email": "priya.patel@example.com"},
        {"name": "Rohan Mehta", "email": "rohan.mehta@example.com"},
        {"name": "Ananya Iyer", "email": "ananya.iyer@example.com"},
    ]

    customer_map: Dict[str, Customer] = {}
    for cust_data in synthetic_customers:
        existing = session.execute(
            select(Customer).where(Customer.email == cust_data["email"])
        ).scalar_one_or_none()
        if existing:
            customer_map[cust_data["email"]] = existing
            stats["customers"]["existing"] += 1
        else:
            cust = Customer(
                name=cust_data["name"],
                email=cust_data["email"],
                created_at=base_time,
            )
            session.add(cust)
            session.flush()
            customer_map[cust_data["email"]] = cust
            stats["customers"]["inserted"] += 1

    # 2. Orders with realistic Indian Rupees pricing in integer paise
    synthetic_orders = [
        {
            "order_number": "ORD-2026-001",
            "customer_email": "alice.chen@example.com",
            "product_name": "Ergonomic Office Chair",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time,
            "expected_delivery_date": base_time + timedelta(days=5),
            "delivered_at": base_time + timedelta(days=4),
            "total_amount": 1999900,  # ₹19,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-003",
            "category": "home_appliances",
        },
        {
            "order_number": "ORD-2026-002",
            "customer_email": "alice.chen@example.com",
            "product_name": "Wireless Mechanical Keyboard",
            "order_status": "processing",
            "delivery_status": "not_shipped",
            "order_date": base_time + timedelta(days=15),
            "expected_delivery_date": base_time + timedelta(days=21),
            "delivered_at": None,
            "total_amount": 899900,  # ₹8,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-001",
            "category": "electronics",
        },
        {
            "order_number": "ORD-2026-003",
            "customer_email": "bob.martinez@example.com",
            "product_name": "Ultra-HD 27-inch Monitor",
            "order_status": "shipped",
            "delivery_status": "delayed",
            "order_date": base_time + timedelta(days=10),
            "expected_delivery_date": base_time + timedelta(days=15),
            "delivered_at": None,
            "total_amount": 3499900,  # ₹34,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-001",
            "category": "electronics",
        },
        {
            "order_number": "ORD-2026-004",
            "customer_email": "bob.martinez@example.com",
            "product_name": "Noise-Cancelling Headphones",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time + timedelta(days=8),
            "expected_delivery_date": base_time + timedelta(days=12),
            "delivered_at": base_time + timedelta(days=12),
            "total_amount": 1499900,  # ₹14,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-001",
            "category": "electronics",
        },
        {
            "order_number": "ORD-2026-005",
            "customer_email": "clara.dupont@example.com",
            "product_name": "USB-C Multi-Port Docking Station",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time + timedelta(days=12),
            "expected_delivery_date": base_time + timedelta(days=16),
            "delivered_at": base_time + timedelta(days=16),
            "total_amount": 499900,  # ₹4,999.00 (under ₹5,000 Tier 1 threshold)
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-001",
            "category": "electronics",
        },
        {
            "order_number": "ORD-2026-006",
            "customer_email": "clara.dupont@example.com",
            "product_name": "Smart Fitness Watch",
            "order_status": "pending",
            "delivery_status": "not_shipped",
            "order_date": base_time + timedelta(days=25),
            "expected_delivery_date": base_time + timedelta(days=30),
            "delivered_at": None,
            "total_amount": 1299900,  # ₹12,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-001",
            "category": "electronics",
        },
        {
            "order_number": "ORD-2026-007",
            "customer_email": "david.kim@example.com",
            "product_name": "4K Webcam with Dual Mics",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time + timedelta(days=7),
            "expected_delivery_date": base_time + timedelta(days=11),
            "delivered_at": base_time + timedelta(days=11),
            "total_amount": 799900,  # ₹7,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-001",
            "category": "electronics",
        },
        {
            "order_number": "ORD-2026-008",
            "customer_email": "elena.rostova@example.com",
            "product_name": "Adjustable Standing Desk",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time + timedelta(days=5),
            "expected_delivery_date": base_time + timedelta(days=10),
            "delivered_at": base_time + timedelta(days=10),
            "total_amount": 4999900,  # ₹49,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-003",
            "category": "home_appliances",
        },
        {
            "order_number": "ORD-2026-009",
            "customer_email": "priya.patel@example.com",
            "product_name": "Pure Cotton Kurta Set",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time + timedelta(days=14),
            "expected_delivery_date": base_time + timedelta(days=18),
            "delivered_at": base_time + timedelta(days=18),
            "total_amount": 189900,  # ₹1,899.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-002",
            "category": "fashion",
        },
        {
            "order_number": "ORD-2026-010",
            "customer_email": "rohan.mehta@example.com",
            "product_name": "Formal Leather Oxford Shoes",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time + timedelta(days=12),
            "expected_delivery_date": base_time + timedelta(days=16),
            "delivered_at": base_time + timedelta(days=16),
            "total_amount": 349900,  # ₹3,499.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-002",
            "category": "fashion",
        },
        {
            "order_number": "ORD-2026-011",
            "customer_email": "ananya.iyer@example.com",
            "product_name": "Inverter Convection Microwave Oven",
            "order_status": "delivered",
            "delivery_status": "delivered",
            "order_date": base_time + timedelta(days=6),
            "expected_delivery_date": base_time + timedelta(days=10),
            "delivered_at": base_time + timedelta(days=10),
            "total_amount": 1899900,  # ₹18,999.00
            "currency": CURRENCY_CODE,
            "seller_id": "SELLER-003",
            "category": "home_appliances",
        },
    ]

    order_map: Dict[str, Order] = {}
    for ord_data in synthetic_orders:
        existing = session.execute(
            select(Order).where(Order.order_number == ord_data["order_number"])
        ).scalar_one_or_none()
        if existing:
            # Additively enrich existing record with INR and seller/category if missing
            if existing.currency == "USD" or existing.currency is None:
                existing.currency = CURRENCY_CODE
                existing.total_amount = ord_data["total_amount"]
            if not existing.seller_id:
                existing.seller_id = ord_data["seller_id"]
            if not existing.category:
                existing.category = ord_data["category"]
            order_map[ord_data["order_number"]] = existing
            stats["orders"]["existing"] += 1
        else:
            cust = customer_map[ord_data["customer_email"]]
            order = Order(
                order_number=ord_data["order_number"],
                customer_id=cust.id,
                product_name=ord_data["product_name"],
                order_status=ord_data["order_status"],
                delivery_status=ord_data["delivery_status"],
                order_date=ord_data["order_date"],
                expected_delivery_date=ord_data["expected_delivery_date"],
                delivered_at=ord_data["delivered_at"],
                total_amount=ord_data["total_amount"],
                currency=ord_data["currency"],
                seller_id=ord_data["seller_id"],
                category=ord_data["category"],
                created_at=ord_data["order_date"],
            )
            session.add(order)
            session.flush()
            order_map[ord_data["order_number"]] = order
            stats["orders"]["inserted"] += 1

    # 3. Support Cases with Indian localized content and INR references
    synthetic_cases = [
        {
            "case_number": "CASE-2026-1001",
            "customer_email": "alice.chen@example.com",
            "order_number": "ORD-2026-002",
            "subject": "Shipment status inquiry - order not yet shipped",
            "complaint_text": "I placed an order for a mechanical keyboard 5 days ago and the tracking still shows not shipped.",
            "status": "open",
            "priority": "medium",
            "resolution_summary": None,
            "created_at": base_time + timedelta(days=20),
            "ticket_number": "TCK-2026-1001",
            "ticket_category": "delivery_delay",
            "event_message": "Case created: customer reported delay in keyboard dispatch.",
        },
        {
            "case_number": "CASE-2026-1002",
            "customer_email": "bob.martinez@example.com",
            "order_number": "ORD-2026-003",
            "subject": "Delivery delayed past promised date",
            "complaint_text": "The monitor was scheduled for delivery 3 days ago. Tracking has been stuck at Hyderabad regional hub.",
            "status": "in_progress",
            "priority": "high",
            "resolution_summary": None,
            "created_at": base_time + timedelta(days=18),
            "ticket_number": "TCK-2026-1002",
            "ticket_category": "delivery_delay",
            "event_message": "Courier carrier inquiry lodged regarding delayed shipment at Hyderabad hub.",
        },
        {
            "case_number": "CASE-2026-1003",
            "customer_email": "clara.dupont@example.com",
            "order_number": "ORD-2026-005",
            "subject": "Damaged port on docking station upon arrival",
            "complaint_text": "The USB-C upstream port on the docking station is bent and does not connect securely.",
            "status": "in_progress",
            "priority": "high",
            "resolution_summary": None,
            "created_at": base_time + timedelta(days=17),
            "ticket_number": "TCK-2026-1003",
            "ticket_category": "damaged_product",
            "event_message": "Photos received confirming port physical defect.",
            "approval_action": "replacement",
            "approval_justification": "Verified physical damage upon unboxing within standard return window.",
        },
        {
            "case_number": "CASE-2026-1004",
            "customer_email": "david.kim@example.com",
            "order_number": "ORD-2026-007",
            "subject": "Refund inquiry - microphone malfunction",
            "complaint_text": "The webcam microphone produces excessive static noise and fails diagnostic checks.",
            "status": "resolved",
            "priority": "medium",
            "resolution_summary": "Full refund of ₹7,999.00 approved under warranty after remote hardware diagnostics.",
            "created_at": base_time + timedelta(days=14),
            "ticket_number": "TCK-2026-1004",
            "ticket_category": "refund_request",
            "event_message": "Refund approval of ₹7,999.00 recorded; awaiting payment gateway processing.",
            "approval_action": "refund",
            "approval_justification": "Hardware audio defect confirmed under 7-day electronics warranty.",
            "approval_status": "approved",
            "feedback_rating": 5,
            "feedback_comment": "Fast and courteous support resolution.",
        },
        {
            "case_number": "CASE-2026-1005",
            "customer_email": "elena.rostova@example.com",
            "order_number": "ORD-2026-008",
            "subject": "Missing assembly hardware in package",
            "complaint_text": "The desk frame box was missing the M6 screw packet and hex wrench.",
            "status": "resolved",
            "priority": "low",
            "resolution_summary": "Expedited replacement hardware kit dispatched via BlueDart tracking #BD-9921.",
            "created_at": base_time + timedelta(days=11),
            "ticket_number": "TCK-2026-1005",
            "ticket_category": "general",
            "event_message": "Replacement screw pack dispatched with priority tracking.",
            "feedback_rating": 4,
            "feedback_comment": "Quick response to supply the missing screws.",
        },
        {
            "case_number": "CASE-2026-1006",
            "customer_email": "priya.patel@example.com",
            "order_number": "ORD-2026-009",
            "subject": "Fashion size exchange request",
            "complaint_text": "The kurta set in size M is too small around the shoulders. I need size L. Tags are intact.",
            "status": "in_progress",
            "priority": "medium",
            "resolution_summary": None,
            "created_at": base_time + timedelta(days=19),
            "ticket_number": "TCK-2026-1006",
            "ticket_category": "replacement_request",
            "event_message": "Doorstep size exchange requested with VastraKart under 14-day policy.",
            "approval_action": "replacement",
            "approval_justification": "Complimentary size exchange requested within 14-day window.",
        },
    ]

    for case_data in synthetic_cases:
        existing_case = session.execute(
            select(SupportCase).where(SupportCase.case_number == case_data["case_number"])
        ).scalar_one_or_none()

        if existing_case:
            case_obj = existing_case
            stats["support_cases"]["existing"] += 1
        else:
            cust = customer_map[case_data["customer_email"]]
            order = order_map.get(case_data["order_number"]) if case_data.get("order_number") else None
            case_obj = SupportCase(
                case_number=case_data["case_number"],
                customer_id=cust.id,
                order_id=order.id if order else None,
                subject=case_data["subject"],
                complaint_text=case_data["complaint_text"],
                status=case_data["status"],
                priority=case_data["priority"],
                resolution_summary=case_data["resolution_summary"],
                created_at=case_data["created_at"],
                updated_at=case_data["created_at"],
            )
            session.add(case_obj)
            session.flush()
            stats["support_cases"]["inserted"] += 1

        # Check or add SupportTicket
        existing_ticket = session.execute(
            select(SupportTicket).where(SupportTicket.ticket_number == case_data["ticket_number"])
        ).scalar_one_or_none()
        if existing_ticket:
            stats["support_tickets"]["existing"] += 1
        else:
            ticket = SupportTicket(
                ticket_number=case_data["ticket_number"],
                case_id=case_obj.id,
                status=case_data["status"],
                category=case_data["ticket_category"],
                created_at=case_data["created_at"],
                updated_at=case_data["created_at"],
            )
            session.add(ticket)
            stats["support_tickets"]["inserted"] += 1

        # Check or add CaseEvent
        existing_event = session.execute(
            select(CaseEvent).where(
                CaseEvent.case_id == case_obj.id,
                CaseEvent.message == case_data["event_message"]
            )
        ).scalar_one_or_none()
        if existing_event:
            stats["case_events"]["existing"] += 1
        else:
            event = CaseEvent(
                case_id=case_obj.id,
                event_type="case_milestone",
                message=case_data["event_message"],
                details_json=None,
                created_at=case_data["created_at"],
            )
            session.add(event)
            stats["case_events"]["inserted"] += 1

        # Check or add ApprovalRequest if present
        if "approval_action" in case_data:
            existing_approval = session.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.case_id == case_obj.id,
                    ApprovalRequest.requested_action == case_data["approval_action"]
                )
            ).scalar_one_or_none()
            if existing_approval:
                stats["approval_requests"]["existing"] += 1
            else:
                approval = ApprovalRequest(
                    case_id=case_obj.id,
                    requested_action=case_data["approval_action"],
                    status=case_data.get("approval_status", "pending"),
                    justification=case_data["approval_justification"],
                    decision_reason="Approved per warranty policy in INR" if case_data.get("approval_status") == "approved" else None,
                    created_at=case_data["created_at"],
                    updated_at=case_data["created_at"],
                )
                session.add(approval)
                stats["approval_requests"]["inserted"] += 1

        # Check or add CustomerFeedback if present
        if "feedback_rating" in case_data:
            existing_feedback = session.execute(
                select(CustomerFeedback).where(CustomerFeedback.case_id == case_obj.id)
            ).scalar_one_or_none()
            if existing_feedback:
                stats["customer_feedback"]["existing"] += 1
            else:
                feedback = CustomerFeedback(
                    case_id=case_obj.id,
                    rating=case_data["feedback_rating"],
                    comments=case_data.get("feedback_comment"),
                    created_at=case_data["created_at"],
                )
                session.add(feedback)
                stats["customer_feedback"]["inserted"] += 1

    # 5. Users (Level 6 RBAC initial demonstration users)
    seed_users_data = [
        {
            "username": "supervisor_alice",
            "password": "SupervisorPassword123!",
            "full_name": "Alice Supervisor",
            "role": "tier2_supervisor",
            "is_active": True,
        },
        {
            "username": "senior_bob",
            "password": "SeniorPassword123!",
            "full_name": "Bob Senior Manager",
            "role": "senior_supervisor",
            "is_active": True,
        },
        {
            "username": "agent_charlie",
            "password": "AgentPassword123!",
            "full_name": "Charlie Frontline",
            "role": "frontline_agent",
            "is_active": True,
        },
        {
            "username": "inactive_dan",
            "password": "DanPassword123!",
            "full_name": "Dan Inactive",
            "role": "tier2_supervisor",
            "is_active": False,
        },
    ]

    for u_data in seed_users_data:
        existing_user = session.execute(
            select(User).where(User.username == u_data["username"])
        ).scalar_one_or_none()
        if existing_user:
            stats["users"]["existing"] += 1
        else:
            new_u = User(
                username=u_data["username"],
                hashed_password=hash_password(u_data["password"]),
                full_name=u_data["full_name"],
                role=u_data["role"],
                is_active=u_data["is_active"],
                created_at=base_time,
            )
            session.add(new_u)
            stats["users"]["inserted"] += 1

    session.commit()
    return stats


if __name__ == "__main__":
    init_db()
    with SessionLocal() as db_session:
        results = seed_database(db_session)
        print("=== Database Seed Summary (INR Localization) ===")
        for entity, counts in results.items():
            print(f" - {entity.capitalize()}: {counts['inserted']} inserted, {counts['existing']} already existed")
        sys.exit(0)
