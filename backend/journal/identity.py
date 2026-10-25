from __future__ import annotations

from fastapi import Request

DEMO_USER_ID = "demo"


def get_current_user_id(_: Request) -> str:
    """Return the isolated demo identity until the application has authentication."""
    return DEMO_USER_ID
