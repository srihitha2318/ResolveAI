"""
Pydantic schemas for ResolveAI Customer Portal and Customer Ownership Verification.
Provides sanitized, customer-safe view representations excluding internal supervisor notes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerVerifyAccessRequest(BaseModel):
    """Payload to securely verify customer ownership of an order or case."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, description="Customer registered email address")
    order_number: Optional[str] = Field(None, description="Optional order number to verify")
    case_number: Optional[str] = Field(None, description="Optional case number to verify")


class CustomerCaseSummary(BaseModel):
    """Safe, minimal summary of a support case for customer listing."""

    model_config = ConfigDict(extra="ignore")

    case_number: str = Field(..., description="Unique case identifier")
    order_number: Optional[str] = Field(None, description="Associated order number")
    product_name: Optional[str] = Field(None, description="Associated product name")
    subject: str = Field(..., description="Complaint subject headline")
    status: str = Field(..., description="Public case status (open, in_progress, resolved, closed, escalated)")
    created_at: datetime = Field(..., description="Submission timestamp")
    clarification_needed: bool = Field(False, description="Whether case is paused awaiting customer input")
    thread_id: Optional[str] = Field(None, description="Workflow thread identifier if clarification is required")


class CustomerAccessResponse(BaseModel):
    """Response payload returned upon successful customer ownership verification."""

    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(..., description="Scoped customer bearer token")
    token_type: str = Field("bearer", description="Token type")
    customer_id: int = Field(..., description="Verified customer ID")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer registered email")
    cases: List[CustomerCaseSummary] = Field(default_factory=list, description="Verified customer cases")


class CustomerCaseDetail(BaseModel):
    """
    Sanitized, customer-safe case details.
    Excludes internal supervisor notes, staff identifiers, and sensitive audit logs.
    """

    model_config = ConfigDict(extra="ignore")

    case_number: str = Field(..., description="Unique case identifier")
    order_number: Optional[str] = Field(None, description="Associated order identifier")
    product_name: Optional[str] = Field(None, description="Associated product name")
    order_status: Optional[str] = Field(None, description="Order fulfillment status")
    delivery_status: Optional[str] = Field(None, description="Order delivery status")
    subject: str = Field(..., description="Complaint subject headline")
    complaint_text: str = Field(..., description="Customer submitted complaint")
    status: str = Field(..., description="Current case status")
    priority: str = Field("medium", description="Case priority level")
    resolution_summary: Optional[str] = Field(None, description="Customer-facing resolution summary")
    ticket_number: Optional[str] = Field(None, description="Associated support ticket identifier if dispatched")
    created_at: datetime = Field(..., description="Case creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Clarification loop metadata
    clarification_needed: bool = Field(False, description="Whether workflow is paused waiting for customer input")
    thread_id: Optional[str] = Field(None, description="Workflow thread identifier for customer clarification")
    clarification_prompt: Optional[str] = Field(None, description="Customer-directed clarification question")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing fields needed from customer")


class CustomerClarificationView(BaseModel):
    """Sanitized view of a workflow paused waiting for customer clarification."""

    model_config = ConfigDict(extra="ignore")

    thread_id: str = Field(..., description="LangGraph checkpoint thread identifier")
    case_number: Optional[str] = Field(None, description="Associated case identifier")
    missing_fields: List[str] = Field(default_factory=list, description="Specific fields missing")
    clarification_prompt: str = Field(..., description="Plain-language clarification request")
    status: str = Field("needs_information", description="Workflow state")
