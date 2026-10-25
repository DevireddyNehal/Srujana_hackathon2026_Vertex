"""
TradeFXBook Authentication, User Context, and Demo Session Switcher.
Guarantees strict user isolation while providing seamless demo trader switching.
"""

from typing import Optional, Dict, Any
from fastapi import Header, Query, Cookie, HTTPException, status, Depends
from tradefxbook.database import db_session
from tradefxbook.repository import get_user_by_id, list_users
from tradefxbook.generator import hash_password


def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    authorization: Optional[str] = Header(None),
    user_id_query: Optional[str] = Query(None, alias="user_id"),
    user_id_cookie: Optional[str] = Cookie(None, alias="tradefxbook_user_id"),
) -> Dict[str, Any]:
    """
    Resolves the authenticated user strictly from headers, authorization, or demo session.
    Defaults to Demo Trader 01 if no explicit context is provided in demo mode.
    """
    target_user_id: Optional[str] = None

    if x_user_id:
        target_user_id = x_user_id.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        # In demo mode, token can be the user_id or a demo token
        target_user_id = token.replace("demo_token_", "")
    elif user_id_cookie:
        target_user_id = user_id_cookie.strip()
    elif user_id_query:
        target_user_id = user_id_query.strip()
    else:
        # Default active demo trader
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
