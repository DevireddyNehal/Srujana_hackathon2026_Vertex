from __future__ import annotations

from fastapi import Request

DEMO_USER_ID = "demo"


def get_current_user_id(request: Request) -> str:
    """Return user id from headers, authorization bearer, query param, or fallback to demo."""
    x_user = request.headers.get("X-User-Id")
    if x_user and x_user.strip():
        return x_user.strip()
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split("Bearer ", 1)[1].strip()
        uid = token.replace("demo_token_", "").replace("token_", "").strip()
        if uid:
            return uid
    cookie = request.cookies.get("tradefxbook_user_id") or request.cookies.get("user_id")
    if cookie and cookie.strip():
        return cookie.strip()
    qid = request.query_params.get("user_id")
    if qid and qid.strip():
        return qid.strip()
    return DEMO_USER_ID

