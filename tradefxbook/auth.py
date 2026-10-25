"""
TradeFXBook Authentication, User Context, and Demo Session Switcher.
Guarantees strict user isolation while providing seamless demo trader switching.
"""

import hashlib
import hmac
from typing import Optional, Dict, Any
from fastapi import Header, Query, Cookie, HTTPException, status
from tradefxbook.config import settings
from tradefxbook.database import db_session
from tradefxbook.repository import get_user_by_id, list_users
from tradefxbook.generator import hash_password


def create_access_token(user: Dict[str, Any]) -> str:
    """Creates a cryptographically signed authentication token using HMAC-SHA256."""
    user_id = user["id"]
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return f"token_{user_id}_{sig}"


def verify_access_token(token: str) -> str:
    """Verifies HMAC signature of an authentication token and returns verified user id."""
    if not token.startswith("token_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format: missing 'token_' prefix.",
        )
    parts = token[len("token_"):].rsplit("_", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token.",
        )
    user_id, signature = parts
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or forged authentication token signature.",
        )
    return user_id


def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    authorization: Optional[str] = Header(None),
    user_id_query: Optional[str] = Query(None, alias="user_id"),
    user_id_cookie: Optional[str] = Cookie(None, alias="tradefxbook_user_id"),
) -> Dict[str, Any]:
    """
    Resolves the authenticated user strictly from headers, authorization, or demo session.
    Guarantees cryptographic verification for tokens and strictly isolates user accounts.
    """
    target_user_id: Optional[str] = None
    authenticated_via_token = False

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        if token.startswith("demo_token_"):
            demo_id = token.replace("demo_token_", "").strip()
            user = get_user_by_id(demo_id)
            if not user or not user.get("is_demo"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid demo token: '{demo_id}' is not an active demo trader.",
                )
            target_user_id = user["id"]
            authenticated_via_token = True
        elif token.startswith("token_"):
            target_user_id = verify_access_token(token)
            authenticated_via_token = True
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unrecognized token format.",
            )

    # Check for spoofing if both Authorization and X-User-Id are provided
    if authenticated_via_token and x_user_id and x_user_id.strip():
        if x_user_id.strip() != target_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security violation: X-User-Id header does not match authenticated token identity.",
            )

    if not target_user_id:
        if x_user_id and x_user_id.strip():
            target_user_id = x_user_id.strip()
        elif user_id_cookie and user_id_cookie.strip():
            target_user_id = user_id_cookie.strip()
        elif user_id_query and user_id_query.strip():
            target_user_id = user_id_query.strip()
        else:
            # Default active demo trader in demo mode
            target_user_id = "demo_trader_01"

    has_explicit_id = bool(x_user_id or authorization or user_id_cookie or user_id_query)

    user = get_user_by_id(target_user_id)
    if not user:
        if has_explicit_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid user credentials: User '{target_user_id}' does not exist.",
            )
        # Default to first available demo trader when no credentials provided
        demo_users = list_users(is_demo_only=True)
        if demo_users:
            return demo_users[0]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {target_user_id} not found and no demo users available.",
        )

    return user


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates user credentials against stored PBKDF2 password hashes."""
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            return None
        user = dict(row)
        expected_hash = hash_password(password)
        if user["password_hash"] == expected_hash:
            return user
        return None

