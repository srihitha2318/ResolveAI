"""
Core Authentication and Role-Based Access Control (RBAC) Subsystem for ResolveAI.
Provides secure password hashing (bcrypt), RFC-compliant HMAC-SHA256 signed bearer tokens,
role-based authorization hierarchies, and FastAPI authentication dependencies.
"""

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import logger
from app.core.policy_rules import HIGH_VALUE_THRESHOLD_PAISE, TIER_1_MAX_AMOUNT_PAISE, format_inr
from app.database.db import get_db
from app.database.models import User, Customer

# RBAC Role Definitions
ROLE_FRONTLINE_AGENT = "frontline_agent"
ROLE_TIER2_SUPERVISOR = "tier2_supervisor"
ROLE_SENIOR_SUPERVISOR = "senior_supervisor"
ROLE_CUSTOMER = "customer"

VALID_ROLES: Set[str] = {
    ROLE_FRONTLINE_AGENT,
    ROLE_TIER2_SUPERVISOR,
    ROLE_SENIOR_SUPERVISOR,
    ROLE_CUSTOMER,
}

# HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password Hashing Utilities
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt rounds."""
    clean_pw = password.strip().encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(clean_pw, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    try:
        clean_pw = plain_password.strip().encode("utf-8")
        clean_hash = hashed_password.strip().encode("utf-8")
        return bcrypt.checkpw(clean_pw, clean_hash)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Signed HMAC-SHA256 Token Utilities (Zero External Dependency)
# ---------------------------------------------------------------------------

def create_access_token(
    username: str,
    role: str,
    user_id: int,
    expires_delta_minutes: Optional[int] = None,
) -> str:
    """
    Creates a signed HMAC-SHA256 bearer token adhering to standard JWT structure.
    Payload contains sub (username), role, uid, exp, and iat claims.
    """
    delta_mins = expires_delta_minutes if expires_delta_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now_ts = int(time.time())
    exp_ts = now_ts + (delta_mins * 60)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "role": role,
        "uid": user_id,
        "exp": exp_ts,
        "iat": now_ts,
    }

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).rstrip(b"=").decode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).rstrip(b"=").decode("utf-8")
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    secret_bytes = settings.SECRET_KEY.encode("utf-8")
    signature = base64.urlsafe_b64encode(
        hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode("utf-8")

    return f"{header_b64}.{payload_b64}.{signature}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a signed HMAC-SHA256 token.
    Enforces signature validity and expiration timestamps.
    Raises ValueError on invalid token, signature mismatch, or expired token.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Token string must not be empty.")

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Malformed token format (expected 3 segments).")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    secret_bytes = settings.SECRET_KEY.encode("utf-8")

    expected_sig = base64.urlsafe_b64encode(
        hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode("utf-8")

    if not hmac.compare_digest(sig_b64, expected_sig):
        raise ValueError("Invalid token signature.")

    # Base64 padding correction
    rem = len(payload_b64) % 4
    if rem:
        payload_b64 += "=" * (4 - rem)

    try:
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception as e:
        raise ValueError(f"Could not parse token payload: {e}")

    # Expiration check
    now_ts = int(time.time())
    if "exp" in payload and payload["exp"] < now_ts:
        raise ValueError("Token has expired.")

    return payload


# ---------------------------------------------------------------------------
# User Authentication Service
# ---------------------------------------------------------------------------

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticates user credentials against the database.
    Returns User instance if valid and active; None otherwise.
    """
    clean_user = username.strip()
    user = db.scalar(select(User).where(User.username == clean_user))
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ---------------------------------------------------------------------------
# RBAC Approval Limits & Permission Verification
# ---------------------------------------------------------------------------

def is_role_authorized_for_approval(role: str, total_amount_paise: int) -> Tuple[bool, str]:
    """
    Validates whether the user's role has authority to approve a claim of given amount.
    - frontline_agent: Cannot approve supervisor review cases.
    - tier2_supervisor: Can approve up to HIGH_VALUE_THRESHOLD_PAISE (₹25,000.00).
    - senior_supervisor: Can approve any claim, including high-value orders.
    """
    if role == ROLE_FRONTLINE_AGENT:
        return False, "Frontline agents are not authorized to approve supervisor review cases."

    if role == ROLE_TIER2_SUPERVISOR:
        if total_amount_paise > HIGH_VALUE_THRESHOLD_PAISE:
            formatted_val = format_inr(total_amount_paise)
            formatted_thresh = format_inr(HIGH_VALUE_THRESHOLD_PAISE)
            return (
                False,
                f"High-value claim ({formatted_val} > {formatted_thresh}) requires senior_supervisor co-authorization.",
            )
        return True, ""

    if role == ROLE_SENIOR_SUPERVISOR:
        return True, ""

    return False, f"Unrecognized role '{role}' is not authorized."


def is_role_authorized_for_rejection(role: str) -> Tuple[bool, str]:
    """
    Validates whether the user's role has authority to reject an escalated claim.
    Frontline agents cannot reject supervisor review cases; supervisors can.
    """
    if role == ROLE_FRONTLINE_AGENT:
        return False, "Frontline agents are not authorized to reject supervisor review cases."

    if role in (ROLE_TIER2_SUPERVISOR, ROLE_SENIOR_SUPERVISOR):
        return True, ""

    return False, f"Unrecognized role '{role}' is not authorized."


# ---------------------------------------------------------------------------
# FastAPI Dependency: Reviewer Context
# ---------------------------------------------------------------------------

class AuthenticatedReviewer:
    """Encapsulates authenticated reviewer context and role for approval endpoints."""

    def __init__(
        self,
        user: Optional[User],
        reviewer_id: str,
        role: str,
        is_dev_fallback: bool = False,
    ):
        self.user = user
        self.reviewer_id = reviewer_id
        self.role = role
        self.is_dev_fallback = is_dev_fallback


def get_current_user_optional(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extracts and validates User from optional Bearer token."""
    if not auth_credentials or not auth_credentials.credentials:
        return None

    try:
        payload = decode_access_token(auth_credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Enforces that a valid authenticated user must be present."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_role(allowed_roles: Union[str, List[str]]):
    """Factory creating dependency to require specific RBAC roles."""
    if isinstance(allowed_roles, str):
        roles_set = {allowed_roles}
    else:
        roles_set = set(allowed_roles)

    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{user.role}' lacks required permissions: {sorted(roles_set)}.",
            )
        return user

    return role_checker


def get_approval_reviewer(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedReviewer:
    """
    Dependency resolving reviewer identity for approval/rejection endpoints:
    1. If Authorization header is provided -> Validates token and user role strictly.
       Raises 401 on bad/expired token, 401 on inactive user.
    2. If NO Authorization header is provided:
       - In production mode (or when fallback disabled): Raises 401 Unauthorized immediately.
         Never permits unauthenticated reviewer fallback in production.
       - In development/testing mode (AUTH_DEV_MODE_FALLBACK=True): Falls back to dev mode
         allowing backward-compatible reviewer_id payloads.
    """
    # 1. Bearer token present
    if auth_credentials and auth_credentials.credentials:
        try:
            payload = decode_access_token(auth_credentials.credentials)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username = payload.get("sub")
        user = db.scalar(select(User).where(User.username == username))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedReviewer(
            user=user,
            reviewer_id=user.username,
            role=user.role,
            is_dev_fallback=False,
        )

    # 2. No token: enforce production boundary
    if settings.is_production or not settings.allow_dev_auth_fallback:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Unauthenticated operations are strictly prohibited in production.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Development / test fallback mode
    return AuthenticatedReviewer(
        user=None,
        reviewer_id="",
        role=ROLE_SENIOR_SUPERVISOR,
        is_dev_fallback=True,
    )


# ---------------------------------------------------------------------------
# Customer Portal Authentication & Ownership Verification
# ---------------------------------------------------------------------------

class AuthenticatedCustomer:
    """Encapsulates authenticated customer session context."""

    def __init__(self, customer_id: int, email: str, name: str):
        self.id = customer_id
        self.customer_id = customer_id
        self.email = email
        self.name = name
        self.role = ROLE_CUSTOMER


def create_customer_token(
    customer_id: int,
    email: str,
    expires_delta_minutes: int = 120,
) -> str:
    """
    Creates a signed HMAC-SHA256 bearer token scoped strictly to customer access.
    """
    return create_access_token(
        username=email,
        role=ROLE_CUSTOMER,
        user_id=customer_id,
        expires_delta_minutes=expires_delta_minutes,
    )


def get_current_customer_optional(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[AuthenticatedCustomer]:
    """Extracts customer identity from optional Bearer token."""
    if not auth_credentials or not auth_credentials.credentials:
        return None

    try:
        payload = decode_access_token(auth_credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = payload.get("role")
    uid = payload.get("uid")
    email = payload.get("sub")

    if role != ROLE_CUSTOMER or not uid or not email:
        return None

    customer = db.scalar(select(Customer).where(Customer.id == uid, Customer.email == email))
    if not customer:
        return None

    return AuthenticatedCustomer(customer_id=customer.id, email=customer.email, name=customer.name)


def get_current_customer(
    customer: Optional[AuthenticatedCustomer] = Depends(get_current_customer_optional),
) -> AuthenticatedCustomer:
    """Enforces that a valid authenticated customer session must be present."""
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer authentication required. Please verify access with registered email and order/case number.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return customer

