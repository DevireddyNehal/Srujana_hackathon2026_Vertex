"""Small in-memory analysis store used by the Srujana F-06 prototype.

The current PLAN.md specifies an in-memory database. Records are lost when
this Python process restarts. Replace this module with SQLite if durable
analysis history becomes a requirement.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

_lock = RLock()
_analyses: dict[str, dict[str, Any]] = {}


def initialize_database() -> None:
    """Initialize the in-memory store.

    Kept as a function so main.py has a stable initialization interface if the
    backing store changes later. It intentionally does not erase existing data.
    """
    return None


def save_analysis(
    *,
    portfolio_id: str | None,
    portfolio_name: str,
    scenario: dict[str, Any],
    result: dict[str, Any],
) -> str:
    """Save an analysis result and return its internal record ID."""
    analysis_id = uuid4().hex
    record = {
        "id": analysis_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio_name,
        "scenario": deepcopy(scenario),
        "result": deepcopy(result),
    }
    with _lock:
        _analyses[analysis_id] = record
    return analysis_id


def get_analysis_by_id(analysis_id: str) -> dict[str, Any] | None:
    """Return a copy of one saved analysis, or None if it does not exist."""
    with _lock:
        record = _analyses.get(analysis_id)
        return deepcopy(record) if record is not None else None


def list_recent_analyses(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recently saved analysis records."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    with _lock:
        records = list(_analyses.values())
    records.sort(key=lambda item: item["created_at"], reverse=True)
    return deepcopy(records[:limit])


def clear_analyses() -> None:
    """Clear stored analyses. Intended for automated tests only."""
    with _lock:
        _analyses.clear()
