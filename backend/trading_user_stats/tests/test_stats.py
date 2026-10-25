from datetime import datetime, timedelta, timezone

import pytest

from trading_user_stats.app import db, stats
from trading_user_stats.app.seed_demo import seed_demo_trades

UTC = timezone.utc


def trade_time(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


@pytest.fixture
def connection():
    conn = db.connect(":memory:")
    db.init_db(conn)
    conn.execute(
        "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("test", "Test Account", "USD", 10_000, "UTC", 0, "2024-01-31"),
    )
    yield conn
    conn.close()


def insert_trades(conn, values):
    rows = []
    for index, value in enumerate(values):
        opened_at = trade_time(value["closed_at"]) - timedelta(hours=1)
        rows.append({
            "id": f"trade-{index}",
            "user_id": "test",
            "instrument": value.get("instrument", "EURUSD"),
            "direction": 1,
            "qty": 1,
            "entry": 1,
            "exit": 1,
            "contract_size": 1,
            "opened_at": opened_at,
            "closed_at": trade_time(value["closed_at"]),
            "gross": value["gross"],
            "setup": value.get("setup"),
            "rule_adhered": value.get("rule_adhered"),
        })
    db.insert_trades(conn, rows, "UTC", False)


def test_overview_metrics_and_drawdown(connection):
    insert_trades(connection, [
        {"closed_at": "2024-01-02T12:00:00", "gross": 100, "setup": "A", "rule_adhered": 1},
        {"closed_at": "2024-01-02T13:00:00", "gross": -50, "setup": "A", "rule_adhered": 0},
        {"closed_at": "2024-01-03T12:00:00", "gross": -200, "setup": "B"},
        {"closed_at": "2024-01-05T12:00:00", "gross": 300, "setup": "B", "rule_adhered": 1},
        {"closed_at": "2024-01-05T13:00:00", "gross": 0, "setup": "B"},
    ])

    result = stats.overview(connection, "test", "custom", "2024-01-01", "2024-01-06")
    assert (result["closed_trades"], result["net_pnl"]) == (5, 150)
    assert result["win_rate"] == {"value": 40.0, "wins": 2, "losses": 2, "break_even": 1}
    assert result["profit_factor"]["value"] == 1.6
    assert result["expectancy"] == 30
    assert result["max_drawdown"]["amount"] == 250
    assert result["daily_pnl"]["totals"]["net_pnl"] == result["net_pnl"]
    assert result["rule_adherence"] == {"evaluated_trades": 3, "adhered": 2, "percent": 66.67}
    assert {row["name"] for row in result["symbols"]} == {"EURUSD"}


def test_date_range_validation(connection):
    with pytest.raises(ValueError, match="on or before"):
        stats.overview(connection, "test", "custom", "2024-01-05", "2024-01-01")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        stats.overview(connection, "test", "custom", "20240101", "2024-01-02")
    with pytest.raises(ValueError, match="after"):
        stats.overview(connection, "test", "custom", "2024-01-01", "2024-02-01")
    with pytest.raises(ValueError, match="only be supplied"):
        stats.overview(connection, "test", "30d", "2024-01-01", "2024-01-02")


def test_session_filter_and_open_trades(connection):
    insert_trades(connection, [
        {"closed_at": "2024-01-02T12:00:00", "gross": 100},
        {"closed_at": "2024-01-03T12:00:00", "gross": -10},
    ])
    connection.execute("UPDATE trades SET session = 'Asian' WHERE id = 'trade-1'")
    connection.execute(
        """INSERT INTO trades
           (id, user_id, instrument, direction, qty, entry, contract_size, opened_at,
            session, gross, net, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("open", "test", "EURUSD", 1, 1, 1, 1, "2024-01-03T10:00:00+00:00",
         "London", 999, 999, "open"),
    )

    result = stats.overview(connection, "test", "all", session="London")
    assert result["closed_trades"] == 1
    assert result["net_pnl"] == 100
    assert result["sessions"][0]["name"] == "London"


def test_account_timezone_dates_and_dst():
    conn = db.connect(":memory:")
    db.init_db(conn)
    conn.execute(
        "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ny", "NY", "USD", 1_000, "America/New_York", 0, "2024-03-11"),
    )
    row = {
        "id": "dst",
        "user_id": "ny",
        "instrument": "EURUSD",
        "direction": 1,
        "qty": 1,
        "entry": 1,
        "exit": 1,
        "contract_size": 1,
        "opened_at": trade_time("2024-03-11T03:00:00"),
        "closed_at": trade_time("2024-03-11T04:30:00"),
        "gross": 1,
    }
    db.insert_trades(conn, [row], "America/New_York", False)
    assert conn.execute("SELECT closed_date FROM trades").fetchone()[0] == "2024-03-11"
    conn.close()


def test_session_classification_is_dst_aware():
    assert db.classify_session(trade_time("2024-07-01T07:30:00")) == "London"
    assert db.classify_session(trade_time("2024-01-02T07:30:00")) == "Asian"
    assert db.classify_session(trade_time("2024-07-06T12:00:00")) == "Off-hours"


def test_demo_seed_is_idempotent_and_preserves_legacy_trades(tmp_path):
    path = tmp_path / "seed.sqlite3"
    assert seed_demo_trades(path, 20) == 20
    connection = db.connect(path)
    try:
        first = [tuple(row) for row in connection.execute("SELECT id, net FROM trades ORDER BY id")]
    finally:
        connection.close()
    assert seed_demo_trades(path, 20) == 20
    connection = db.connect(path)
    try:
        second = [tuple(row) for row in connection.execute("SELECT id, net FROM trades ORDER BY id")]
        assert first == second
    finally:
        connection.close()

    legacy = db.connect(":memory:")
    legacy.execute("CREATE TABLE trades (trade_id TEXT PRIMARY KEY, symbol TEXT NOT NULL)")
    legacy.execute("INSERT INTO trades VALUES ('old-1', 'EURUSD')")
    db.init_db(legacy)
    assert legacy.execute("SELECT symbol FROM trades_legacy_1").fetchone()[0] == "EURUSD"
    assert "id" in {row["name"] for row in legacy.execute("PRAGMA table_info(trades)")}
    legacy.close()
