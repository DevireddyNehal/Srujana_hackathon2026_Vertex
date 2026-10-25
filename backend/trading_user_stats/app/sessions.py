from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
UTC = timezone.utc
TRADING_SESSIONS = (
    ("London", "Europe/London", 8, 16),
    ("New York", "America/New_York", 8, 17),
    ("Asian", "Asia/Tokyo", 9, 17),
)


def classify_session(timestamp: datetime) -> str:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("trade timestamp must include a timezone")
    for name, timezone_name, start_hour, end_hour in TRADING_SESSIONS:
        local = timestamp.astimezone(ZoneInfo(timezone_name))
        if local.weekday() < 5 and start_hour <= local.hour < end_hour:
            return name
    return "Off-hours"


def classify_market_session(timestamp: str | datetime) -> tuple[str, str]:
    """Return New York market date and session, correctly accounting for DST."""
    if isinstance(timestamp, str):
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        parsed = timestamp
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")

    local = parsed.astimezone(NEW_YORK)
    market_date = local.date().isoformat()
    if local.weekday() >= 5:
        return market_date, "weekend"

    local_time = local.timetz().replace(tzinfo=None)
    if time(9, 30) <= local_time < time(16, 0):
        session = "regular"
    elif local_time < time(9, 30):
        session = "premarket"
    else:
        session = "afterhours"
    return market_date, session
