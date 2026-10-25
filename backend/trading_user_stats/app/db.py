from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    currency TEXT NOT NULL,
    start_balance REAL NOT NULL CHECK (start_balance > 0),
    tz TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    data_end TEXT
);
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES accounts(user_id),
    instrument TEXT NOT NULL,
    direction INTEGER NOT NULL CHECK (direction IN (-1, 1)),
    qty REAL NOT NULL CHECK (qty > 0),
    entry REAL NOT NULL CHECK (entry > 0),
    exit REAL,
    contract_size REAL NOT NULL CHECK (contract_size > 0),
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    closed_date TEXT,
    setup TEXT,
    session TEXT NOT NULL,
    gross REAL NOT NULL,
    commission REAL NOT NULL DEFAULT 0 CHECK (commission >= 0),
    fees REAL NOT NULL DEFAULT 0 CHECK (fees >= 0),
    slippage REAL NOT NULL DEFAULT 0 CHECK (slippage >= 0),
    swap REAL NOT NULL DEFAULT 0,
    net REAL NOT NULL,
    rule_adhered INTEGER CHECK (rule_adhered IN (0, 1) OR rule_adhered IS NULL),
    status TEXT NOT NULL DEFAULT 'closed' CHECK (status IN ('open', 'closed')),
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    CHECK ((status = 'open' AND closed_at IS NULL AND closed_date IS NULL)
        OR (status = 'closed' AND closed_at IS NOT NULL AND closed_date IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_stats_trades_user_date
    ON trades (user_id, status, closed_date);
CREATE INDEX IF NOT EXISTS ix_stats_trades_user_closed
    ON trades (user_id, status, closed_at);
"""

REQUIRED_COLUMNS = {
    "accounts": {"user_id", "name", "currency", "start_balance", "tz", "is_demo", "data_end"},
    "trades": {
        "id", "user_id", "instrument", "direction", "qty", "entry", "exit",
        "contract_size", "opened_at", "closed_at", "closed_date", "setup",
        "session", "gross", "commission", "fees", "slippage", "swap", "net",
        "rule_adhered", "status", "is_demo",
    },
}

SESSIONS = (
    ("London", "Europe/London", 8, 16),
    ("New York", "America/New_York", 8, 17),
    ("Asian", "Asia/Tokyo", 9, 17),
)


def connect(path: str | Path) -> sqlite3.Connection:
    if str(path) == ":memory:":
        connection = sqlite3.connect(":memory:", timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection
    database_path = Path(path).expanduser()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    """Create the schema. Never renames or alters tables it did not create.

    Rows are read by position, so this works with any row_factory.
    """
    for table, required in REQUIRED_COLUMNS.items():
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        if not exists:
            continue
        # PRAGMA table_info rows: (cid, name, type, notnull, dflt_value, pk)
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        missing = required - columns
        if missing:
            raise RuntimeError(
                f"Existing table '{table}' is not compatible with the trading-stats "
                f"schema (missing columns: {', '.join(sorted(missing))}). Point "
                f"TRADING_DB at a separate database file, or rename/migrate that table "
                f"yourself; it will not be modified automatically."
            )
    connection.executescript(SCHEMA)


def classify_session(timestamp):
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("trade timestamp must include a timezone")
    for name, timezone_name, start_hour, end_hour in SESSIONS:
        local = timestamp.astimezone(ZoneInfo(timezone_name))
        if local.weekday() < 5 and start_hour <= local.hour < end_hour:
            return name
    return "Off-hours"


def net_pnl(gross, commission, fees, slippage, swap):
    return round(gross - commission - fees - slippage + swap, 2)


def insert_trades(
    connection: sqlite3.Connection,
    rows: list[dict],
    timezone_name: str,
    is_demo: bool,
) -> None:
    from datetime import timezone

    account_timezone = ZoneInfo(timezone_name)
    output = []
    for trade in rows:
        opened = trade["opened_at"]
        closed = trade.get("closed_at")
        status = trade.get("status", "closed")
        if opened.tzinfo is None or opened.utcoffset() is None:
            raise ValueError(f"trade {trade['id']} opened_at must include a timezone")
        if status not in {"open", "closed"}:
            raise ValueError(f"trade {trade['id']} has invalid status")
        if status == "closed":
            if closed is None or closed.tzinfo is None or closed.utcoffset() is None:
                raise ValueError(f"closed trade {trade['id']} requires a timezone-aware closed_at")
            if closed <= opened:
                raise ValueError(f"trade {trade['id']} must close after it opens")
        elif closed is not None:
            raise ValueError(f"open trade {trade['id']} cannot have closed_at")

        commission = float(trade.get("commission", 0))
        fees = float(trade.get("fees", 0))
        slippage = float(trade.get("slippage", 0))
        swap = float(trade.get("swap", 0))
        record = {
            "id": trade["id"],
            "user_id": trade["user_id"],
            "instrument": trade["instrument"],
            "direction": trade["direction"],
            "qty": trade["qty"],
            "entry": trade["entry"],
            "exit": trade.get("exit"),
            "contract_size": trade["contract_size"],
            "opened_at": opened.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "closed_at": closed.astimezone(timezone.utc).isoformat(timespec="seconds") if closed else None,
            "closed_date": closed.astimezone(account_timezone).date().isoformat() if closed else None,
            "setup": trade.get("setup"),
            "session": classify_session(opened),
            "gross": trade["gross"],
            "commission": commission,
            "fees": fees,
            "slippage": slippage,
            "swap": swap,
            "net": net_pnl(trade["gross"], commission, fees, slippage, swap),
            "rule_adhered": trade.get("rule_adhered"),
            "status": status,
            "is_demo": int(is_demo),
        }
        output.append(record)

    if output:
        columns = tuple(output[0])
        connection.executemany(
            f"INSERT INTO trades ({','.join(columns)}) "
            f"VALUES ({','.join(':' + column for column in columns)})",
            output,
        )