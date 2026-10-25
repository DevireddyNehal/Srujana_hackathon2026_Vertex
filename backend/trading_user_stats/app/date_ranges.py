from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

PRESETS = ("7d", "30d", "90d", "ytd", "1y", "all", "custom")
MAX_CUSTOM_DAYS = 3_700


class DateRangeError(ValueError):
    """Raised when a requested statistics range is invalid."""


@dataclass(frozen=True)
class DateRange:
    start: date | None
    end: date
    preset: str


def resolve_date_range(
    preset: str = "30d",
    start: str | None = None,
    end: str | None = None,
    *,
    today: date | None = None,
    earliest: date | None = None,
) -> DateRange:
    today = today or date.today()
    if preset not in PRESETS:
        raise DateRangeError(f"range must be one of: {', '.join(PRESETS)}")

    if preset == "custom":
        if not start or not end:
            raise DateRangeError("custom range requires both start and end dates")
        try:
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
        except ValueError as exc:
            raise DateRangeError("dates must use YYYY-MM-DD format") from exc
        if start_date.isoformat() != start or end_date.isoformat() != end:
            raise DateRangeError("dates must use YYYY-MM-DD format")
        if start_date > end_date:
            raise DateRangeError("start date must be on or before end date")
        if end_date > today:
            raise DateRangeError("end date cannot be in the future")
        if (end_date - start_date).days + 1 > MAX_CUSTOM_DAYS:
            raise DateRangeError(f"custom range cannot exceed {MAX_CUSTOM_DAYS} days")
        return DateRange(start_date, end_date, preset)

    if start is not None or end is not None:
        raise DateRangeError("start and end may only be supplied with range=custom")
    if preset == "all":
        return DateRange(earliest, today, preset)
    if preset == "ytd":
        return DateRange(date(today.year, 1, 1), today, preset)
    days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}[preset]
    return DateRange(today - timedelta(days=days - 1), today, preset)
