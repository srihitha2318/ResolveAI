from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Returns current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    support_cases: Mapped[List["SupportCase"]] = relationship("SupportCase", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email='{self.email}'>"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    order_status: Mapped[str] = mapped_column(String(64), nullable=False)  # pending, processing, shipped, delivered, cancelled
    delivery_status: Mapped[str] = mapped_column(String(64), nullable=False)  # not_shipped, in_transit, delayed, delivered
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_delivery_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # minor units (paise in INR, e.g. ₹1,499.00 = 149900 paise)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    seller_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)  # SELLER-001, SELLER-002, SELLER-003
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)   # electronics, fashion, home_appliances, general_merchandise
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    support_cases: Mapped[List["SupportCase"]] = relationship("SupportCase", back_populates="order")

    def __repr__(self) -> str:
        return f"<Order id={self.id} order_number='{self.order_number}' currency='{self.currency}'>"


class SupportCase(Base):
    __tablename__ = "support_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    complaint_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="open", nullable=False)  # open, in_progress, resolved, closed, escalated
    priority: Mapped[str] = mapped_column(String(64), default="medium", nullable=False)  # low, medium, high, urgent
    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="support_cases")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="support_cases")
    tickets: Mapped[List["SupportTicket"]] = relationship("SupportTicket", back_populates="case", cascade="all, delete-orphan")
    approval_requests: Mapped[List["ApprovalRequest"]] = relationship("ApprovalRequest", back_populates="case", cascade="all, delete-orphan")
    events: Mapped[List["CaseEvent"]] = relationship("CaseEvent", back_populates="case", cascade="all, delete-orphan")
    call_summaries: Mapped[List["CallSummary"]] = relationship("CallSummary", back_populates="case", cascade="all, delete-orphan")
    feedback: Mapped[List["CustomerFeedback"]] = relationship("CustomerFeedback", back_populates="case", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SupportCase id={self.id} case_number='{self.case_number}'>"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="open", nullable=False)  # open, in_progress, closed
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # delivery_delay, damaged_product, refund_request, general
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="tickets")

    def __repr__(self) -> str:
        return f"<SupportTicket id={self.id} ticket_number='{self.ticket_number}'>"


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)  # LangGraph checkpoint thread_id
    requested_action: Mapped[str] = mapped_column(String(100), nullable=False)  # refund, replacement, store_credit, policy_exception, supervisor_review
    status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)  # pending, approved, rejected
    workflow_status: Mapped[str] = mapped_column(String(64), default="pending_review", nullable=False)  # pending_review, approved, rejected, completed
    justification: Mapped[str] = mapped_column(Text, nullable=False)  # escalation reason
    proposed_resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-serialized recommendation
    policy_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-serialized policy passages
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # supervisor identity
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # supervisor notes/rationale
    decision_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Level 6 Approval SLA Tracking
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sla_priority: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)  # standard, high
    required_role: Mapped[str] = mapped_column(String(64), default="tier2_supervisor", nullable=False)  # tier2_supervisor, senior_supervisor
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="approval_requests")

    def __repr__(self) -> str:
        return f"<ApprovalRequest id={self.id} case_id={self.case_id} thread_id='{self.thread_id}' status='{self.status}'>"


class CaseEvent(Base):
    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # case_opened, evidence_attached, status_updated
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="events")

    def __repr__(self) -> str:
        return f"<CaseEvent id={self.id} event_type='{self.event_type}'>"


class CallSummary(Base):
    __tablename__ = "call_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="call_summaries")

    def __repr__(self) -> str:
        return f"<CallSummary id={self.id} case_id={self.case_id}>"


class CustomerFeedback(Base):
    __tablename__ = "customer_feedback"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("support_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case: Mapped["SupportCase"] = relationship("SupportCase", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<CustomerFeedback id={self.id} rating={self.rating}>"


class User(Base):
    """
    Level 6: User model for supervisor authentication and Role-Based Access Control (RBAC).
    Supported roles: frontline_agent, tier2_supervisor, senior_supervisor.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # frontline_agent, tier2_supervisor, senior_supervisor
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"

