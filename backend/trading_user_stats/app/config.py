from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PACKAGE_ROOT / "trading_stats.sqlite3"


@dataclass(frozen=True)
class Settings:
    database_path: Path = DEFAULT_DB_PATH
    demo_trade_count: int = 100_000
    seed_demo_on_startup: bool = True


def get_settings() -> Settings:
    raw_count = os.getenv("TRADING_STATS_DEMO_TRADE_COUNT", "100000")
    try:
        count = int(raw_count)
    except ValueError as exc:
        raise ValueError("TRADING_STATS_DEMO_TRADE_COUNT must be an integer") from exc
    if count < 0:
        raise ValueError("TRADING_STATS_DEMO_TRADE_COUNT cannot be negative")

    raw_seed = os.getenv("TRADING_STATS_SEED_DEMO", "true").strip().lower()
    if raw_seed not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError("TRADING_STATS_SEED_DEMO must be true or false")

    return Settings(
        database_path=Path(os.getenv("TRADING_STATS_DB_PATH", str(DEFAULT_DB_PATH))).expanduser(),
        demo_trade_count=count,
        seed_demo_on_startup=raw_seed in {"true", "1", "yes"},
    )
