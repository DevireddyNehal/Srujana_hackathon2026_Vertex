"""
TradeFXBook Database Engine and Connection Management.
Optimized for high-performance querying on 100,000+ trade records using SQLite with
WAL mode, memory temp store, foreign keys, and composite indexes.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from tradefxbook.config import settings


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    starting_balance REAL NOT NULL DEFAULT 50000.0,
    currency TEXT NOT NULL DEFAULT 'USD',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    is_demo INTEGER NOT NULL DEFAULT 0,
    profile_description TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    direction TEXT NOT NULL,
    status TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0,
    entry_time TEXT NOT NULL,
    exit_time TEXT,
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    contract_size REAL NOT NULL DEFAULT 100000.0,
    account_currency TEXT NOT NULL DEFAULT 'USD',
    stop_loss_price REAL,
    take_profit_price REAL,
    planned_risk_amount REAL,
    risk_pct_balance REAL,
    planned_rr_ratio REAL,
    realized_r_multiple REAL,
    gross_pnl REAL NOT NULL DEFAULT 0.0,
    commission REAL NOT NULL DEFAULT 0.0,
    other_fees REAL NOT NULL DEFAULT 0.0,
    signed_swap_adjustment REAL NOT NULL DEFAULT 0.0,
    net_pnl REAL NOT NULL DEFAULT 0.0,
    strategy_or_setup TEXT,
    trading_session TEXT,
    tags TEXT,
    notes TEXT,
    emotional_state TEXT,
    plan_followed INTEGER DEFAULT 1,
    mistakes_or_lessons TEXT,
    seed_batch TEXT,
    device_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Essential Performance Indexes for Filtering, Aggregations, and Pagination
CREATE INDEX IF NOT EXISTS idx_trades_user_status_exit ON trades(user_id, status, exit_time);
CREATE INDEX IF NOT EXISTS idx_trades_user_status_exit_net ON trades(user_id, status, exit_time, net_pnl);
CREATE INDEX IF NOT EXISTS idx_trades_user_exit ON trades(user_id, exit_time);
CREATE INDEX IF NOT EXISTS idx_trades_user_symbol ON trades(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_trades_user_strategy ON trades(user_id, strategy_or_setup);
CREATE INDEX IF NOT EXISTS idx_trades_user_session ON trades(user_id, trading_session);
CREATE INDEX IF NOT EXISTS idx_trades_is_demo ON trades(is_demo);
CREATE INDEX IF NOT EXISTS idx_trades_seed_batch ON trades(seed_batch);
CREATE INDEX IF NOT EXISTS idx_trades_device_id ON trades(device_id);
CREATE INDEX IF NOT EXISTS idx_trades_user_device ON trades(user_id, device_id);
CREATE INDEX IF NOT EXISTS idx_trades_user_status_net_pnl ON trades(user_id, status, net_pnl);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Creates and configures an optimized SQLite connection.
    """
    target = Path(db_path or settings.DB_PATH)
    if str(target) != ":memory:":
        target.parent.mkdir(parents=True, exist_ok=True)
    target_path = str(target)
    conn = sqlite3.connect(target_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn


@contextmanager
def db_session(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing safe commit/rollback database transactions.
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initializes database schema and ensures all indexes exist safely without dropping data.
    """
    with db_session(db_path) as conn:
        # Ensure backwards-compatible column migration for pre-existing databases before index creation
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        if cursor.fetchone():
            col_cursor = conn.execute("PRAGMA table_info(trades)")
            columns = [row["name"] for row in col_cursor.fetchall()]
            if "device_id" not in columns:
                conn.execute("ALTER TABLE trades ADD COLUMN device_id TEXT;")
        conn.executescript(SCHEMA_SQL)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_device_id ON trades(device_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_device ON trades(user_id, device_id);")
