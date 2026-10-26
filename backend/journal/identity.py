from __future__ import annotations

from fastapi import Request

DEMO_USER_ID = "demo"


def get_current_user_id(request: Request) -> str:
    """Return user id from headers, authorization bearer, query param, or fallback to demo with device isolation."""
    x_device = request.headers.get("X-Device-Id")
    device_suffix = f"_{x_device.strip()}" if x_device and x_device.strip() else ""

    uid = None
    x_user = request.headers.get("X-User-Id")
    if x_user and x_user.strip():
        uid = x_user.strip()
    else:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split("Bearer ", 1)[1].strip()
            candidate = token.replace("demo_token_", "").replace("token_", "").strip()
            if candidate:
                uid = candidate

    if not uid:
        cookie = request.cookies.get("tradefxbook_user_id") or request.cookies.get("user_id")
        if cookie and cookie.strip():
            uid = cookie.strip()

    if not uid:
        qid = request.query_params.get("user_id")
        if qid and qid.strip():
            uid = qid.strip()

    if not uid:
        uid = DEMO_USER_ID

    if device_suffix and (uid == "demo" or uid.startswith("demo_")):
        return f"{uid}{device_suffix}"

    return uid

