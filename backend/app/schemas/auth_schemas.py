"""
Pydantic schemas for ResolveAI Level 6 Authentication and Role-Based Access Control (RBAC).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Payload for user credentials authentication."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, description="Registered username")
    password: str = Field(..., min_length=1, description="Plaintext password")


class UserResponse(BaseModel):
    """Serialized representation of an authenticated user profile."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., description="Unique user database identifier")
    username: str = Field(..., description="Unique user login handle")
    full_name: str = Field(..., description="Full display name of user")
    role: str = Field(..., description="Assigned RBAC role (frontline_agent, tier2_supervisor, senior_supervisor)")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")


class TokenResponse(BaseModel):
    """Bearer token response payload upon successful authentication."""

    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(..., description="Signed HMAC-SHA256 bearer token")
    token_type: str = Field("bearer", description="Token type header standard")
    user: UserResponse = Field(..., description="Authenticated user metadata")
