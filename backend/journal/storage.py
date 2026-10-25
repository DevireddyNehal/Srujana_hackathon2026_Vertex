from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .metrics import trade_metrics
from .schemas import TradeCreate

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "trading_journal.sqlite3"
TRADE_FIELDS = (
    "symbol", "side", "quantity", "entry_price", "exit_price", "opened_at",
    "closed_at", "fees", "stop_loss", "strategy", "setup", "notes", "tags",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS journal_trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('long', 'short')),
    quantity REAL NOT NULL CHECK (quantity > 0),
    entry_price REAL NOT NULL CHECK (entry_price > 0),
    exit_price REAL,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    fees REAL NOT NULL CHECK (fees >= 0),
    stop_loss REAL,
    strategy TEXT NOT NULL,
    setup TEXT NOT NULL,
    notes TEXT NOT NULL,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK ((exit_price IS NULL AND closed_at IS NULL) OR (exit_price IS NOT NULL AND closed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_journal_user_closed
    ON journal_trades (user_id, closed_at);
CREATE INDEX IF NOT EXISTS idx_journal_user_symbol
    ON journal_trades (user_id, symbol);
"""


def database_path() -> Path:
    return Path(os.getenv("TRADING_JOURNAL_DB_PATH", str(DEFAULT_DATABASE))).expanduser()


def _connect(path: str | Path | None = None) -> sqlite3.Connection:
    target = Path(path) if path is not None else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


@contextmanager
def _connection(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = _connect(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_storage(path: str | Path | None = None) -> None:
    with _connection(path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(SCHEMA)


def _serialize_trade(row: sqlite3.Row) -> dict[str, Any]:
    trade = dict(row)
    trade["tags"] = json.loads(trade["tags"])
    trade.update(trade_metrics(trade))
    return trade


def create_trade(user_id: str, request: TradeCreate, path: str | Path | None = None) -> dict[str, Any]:
    values = request.model_dump()
    values["opened_at"] = values["opened_at"].astimezone(timezone.utc).isoformat()
    if values["closed_at"] is not None:
        values["closed_at"] = values["closed_at"].astimezone(timezone.utc).isoformat()
    values["tags"] = json.dumps(values["tags"], separators=(",", ":"))
    now = datetime.now(timezone.utc).isoformat()
    trade_id = uuid4().hex
    with _connection(path) as connection:
        connection.execute(
            f"""INSERT INTO journal_trades
                (id, user_id, {", ".join(TRADE_FIELDS)}, created_at, updated_at)
                VALUES ({", ".join("?" for _ in range(len(TRADE_FIELDS) + 4))})""",
            (trade_id, user_id, *(values[field] for field in TRADE_FIELDS), now, now),
        )
        row = connection.execute(
            "SELECT * FROM journal_trades WHERE id = ? AND user_id = ?",
            (trade_id, user_id),
        ).fetchone()
    if row is None:
        raise RuntimeError("Created trade could not be read back from journal storage")
    return _serialize_trade(row)


def list_trades(
    user_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
    status: str = "all",
    symbol: str | None = None,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conditions = ["user_id = ?"]
    parameters: list[Any] = [user_id]
    if status == "open":
        conditions.append("closed_at IS NULL")
    elif status == "closed":
        conditions.append("closed_at IS NOT NULL")
    if symbol:
        conditions.append("symbol = ?")
        parameters.append(symbol.upper())
    where = " AND ".join(conditions)
    with _connection(path) as connection:
        total = int(connection.execute(
            f"SELECT COUNT(*) FROM journal_trades WHERE {where}", parameters
        ).fetchone()[0])
        rows = connection.execute(
            f"""SELECT * FROM journal_trades WHERE {where}
                ORDER BY COALESCE(closed_at, opened_at) DESC, created_at DESC
                LIMIT ? OFFSET ?""",
            (*parameters, limit, offset),
        ).fetchall()
    return [_serialize_trade(row) for row in rows], total


def get_trade(user_id: str, trade_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    with _connection(path) as connection:
        row = connection.execute(
            "SELECT * FROM journal_trades WHERE id = ? AND user_id = ?",
            (trade_id, user_id),
        ).fetchone()
    return _serialize_trade(row) if row else None


def update_trade(
    user_id: str,
    trade_id: str,
    changes: dict[str, Any],
    path: str | Path | None = None,
) -> dict[str, Any] | None:
    if not changes:
        raise ValueError("at least one trade field must be supplied")
    existing = get_trade(user_id, trade_id, path)
    if existing is None:
        return None

    candidate = {field: existing[field] for field in TRADE_FIELDS}
    candidate.update(changes)
    for field in ("opened_at", "closed_at"):
        value = candidate[field]
        if isinstance(value, datetime):
            candidate[field] = value.astimezone(timezone.utc).isoformat()
    if candidate["exit_price"] is None and candidate["closed_at"] is not None:
        raise ValueError("closed_at requires exit_price")
    if candidate["exit_price"] is not None and candidate["closed_at"] is None:
        raise ValueError("exit_price requires closed_at")
    if candidate["closed_at"] is not None:
        opened = datetime.fromisoformat(candidate["opened_at"])
        closed = datetime.fromisoformat(candidate["closed_at"])
        if closed <= opened:
            raise ValueError("closed_at must be later than opened_at")
    if candidate["stop_loss"] is not None:
        if candidate["side"] == "long" and candidate["stop_loss"] >= candidate["entry_price"]:
            raise ValueError("a long trade stop_loss must be below entry_price")
        if candidate["side"] == "short" and candidate["stop_loss"] <= candidate["entry_price"]:
            raise ValueError("a short trade stop_loss must be above entry_price")

    normalized: dict[str, Any] = {}
    for field, value in changes.items():
        if field in {"opened_at", "closed_at"} and value is not None:
            value = value.astimezone(timezone.utc).isoformat()
        elif field == "tags":
            value = json.dumps(value, separators=(",", ":"))
        normalized[field] = value
    assignments = ", ".join(f"{field} = ?" for field in normalized)
    with _connection(path) as connection:
        connection.execute(
            f"""UPDATE journal_trades SET {assignments}, updated_at = ?
                WHERE id = ? AND user_id = ?""",
            (*normalized.values(), datetime.now(timezone.utc).isoformat(), trade_id, user_id),
        )
    return get_trade(user_id, trade_id, path)


def delete_trade(user_id: str, trade_id: str, path: str | Path | None = None) -> bool:
    with _connection(path) as connection:
        cursor = connection.execute(
            "DELETE FROM journal_trades WHERE id = ? AND user_id = ?",
            (trade_id, user_id),
        )
    return cursor.rowcount > 0


def list_closed_trades(user_id: str, path: str | Path | None = None) -> list[dict[str, Any]]:
    with _connection(path) as connection:
        rows = connection.execute(
            """SELECT * FROM journal_trades WHERE user_id = ? AND closed_at IS NOT NULL
               ORDER BY closed_at, id""",
            (user_id,),
        ).fetchall()
    return [_serialize_trade(row) for row in rows]
