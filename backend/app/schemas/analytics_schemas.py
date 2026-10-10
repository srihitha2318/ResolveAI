"""
Pydantic schemas for ResolveAI Analytics and Operational Reporting.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CategoryBreakdown(BaseModel):
    category: str = Field(..., description="Product category name")
    count: int = Field(..., description="Number of cases or orders")


class StatusBreakdown(BaseModel):
    status: str = Field(..., description="Case or workflow status")
    count: int = Field(..., description="Count of occurrences")


class RecentCaseActivity(BaseModel):
    case_number: str = Field(..., description="Support case number")
    subject: str = Field(..., description="Case subject")
    status: str = Field(..., description="Current status")
    created_at: str = Field(..., description="ISO creation timestamp")


class AnalyticsOverviewResponse(BaseModel):
    """Aggregated operational metrics computed directly from database records."""

    model_config = ConfigDict(extra="ignore")

    total_cases: int = Field(0, description="Total recorded support cases")
    open_cases: int = Field(0, description="Support cases with status 'open'")
    in_progress_cases: int = Field(0, description="Support cases with status 'in_progress'")
    resolved_cases: int = Field(0, description="Support cases with status 'resolved'")
    closed_cases: int = Field(0, description="Support cases with status 'closed'")
    escalated_cases: int = Field(0, description="Support cases with status 'escalated'")

    pending_approvals: int = Field(0, description="Approval requests awaiting review")
    approved_count: int = Field(0, description="Completed approvals")
    rejected_count: int = Field(0, description="Rejected requests")
    sla_breaches: int = Field(0, description="Cases that exceeded approval SLA")
    pending_clarifications: int = Field(0, description="Workflows awaiting customer clarification")

    category_distribution: List[CategoryBreakdown] = Field(default_factory=list, description="Cases grouped by category")
    status_distribution: List[StatusBreakdown] = Field(default_factory=list, description="Cases grouped by status")
    recent_activity: List[RecentCaseActivity] = Field(default_factory=list, description="Recently filed support cases")
