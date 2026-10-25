"""
Automated Test Suite for TradeFXBook Trading Journal and Analytics.
Covers:
- Dataset Integrity (10 demo users, 10,000 trades/user, 100,000 total, unique IDs, idempotency)
- Statistical Correctness (22 metrics, win rate excl. BE, profit factor, max drawdown, continuous daily P&L)
- User Isolation and Security (prevent unauthorized cross-account access, CSV isolation)
- API Endpoint Behaviors and Validation
- High-Performance Query Benchmarks on 100,000 Records
"""

import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tradefxbook.config import settings
from tradefxbook.database import db_session, init_db
from tradefxbook.generator import (
    seed_demo_dataset,
    check_demo_dataset_status,
    reset_demo_data,
)
from tradefxbook.calculations import (
    compute_trade_pnl,
    compute_aggregate_metrics,
    generate_daily_pnl_series,
)
from tradefxbook.repository import (
    get_user_by_id,
    list_users,
    get_trade_by_id,
    create_trade,
    update_trade,
    delete_trade,
    list_trades_paginated,
    export_trades_to_csv,
    get_user_closed_trades,
)
from tradefxbook.api import app
from tradefxbook.verify import verify_dataset


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded_database():
    """Ensures the 100,000 demo dataset is populated once for the test session."""
    init_db()
    status = check_demo_dataset_status()
    if not status["is_complete"]:
        seed_demo_dataset()


@pytest.fixture
def api_client():
    """FastAPI TestClient for TradeFXBook."""
    return TestClient(app)


# ==============================================================================
# 1. DEMO DATASET INTEGRITY TESTS
# ==============================================================================

def test_dataset_exact_counts_and_distribution():
    """Verify exactly 10 demo users, 10,000 trades per user, and 100,000 total closed trades."""
    verification = verify_dataset(verbose=False)
    assert verification["all_passed"] is True, f"Integrity failed: {verification['checks']}"
    assert verification["demo_users_count"] == 10
    assert verification["total_seeded_trades"] == 100_000
    assert verification["total_closed_trades"] == 100_000

    trades_per_user = verification["trades_per_user"]
    assert len(trades_per_user) == 10
    for u_id, stats in trades_per_user.items():
        assert stats["total"] == 10_000, f"User {u_id} does not have 10,000 trades: {stats['total']}"
        assert stats["closed"] == 10_000, f"User {u_id} does not have 10,000 closed trades: {stats['closed']}"


def test_dataset_uniqueness_and_demo_designation():
    """Verify all 100,000 demo trades have is_demo=1 and unique trade IDs."""
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as total_demo,
                   COUNT(DISTINCT id) as unique_ids,
                   SUM(CASE WHEN is_demo = 1 THEN 1 ELSE 0 END) as demo_flagged
            FROM trades
            WHERE seed_batch = ?
            """,
            (settings.DEMO_SEED_BATCH,),
        ).fetchone()

        assert row["total_demo"] == 100_000
        assert row["unique_ids"] == 100_000
        assert row["demo_flagged"] == 100_000


def test_dataset_timestamps_and_no_future_exits():
    """Verify exit_time >= entry_time for all 100,000 seeded trades."""
    with db_session() as conn:
        anomalies = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM trades
            WHERE seed_batch = ? AND exit_time < entry_time
            """,
            (settings.DEMO_SEED_BATCH,),
        ).fetchone()["cnt"]
        assert anomalies == 0


def test_seed_idempotency_does_not_duplicate():
    """Verify re-running the seed command does not create duplicate rows."""
    res = seed_demo_dataset(force_reseed=False)
    assert res["status"] in ("ALREADY_SEEDED", "SUCCESSFULLY_SEEDED")
    status = check_demo_dataset_status()
    assert status["demo_trades_count"] == 100_000
    assert status["demo_users_count"] == 10


def test_demo_reset_preserves_non_demo_users_and_trades(tmp_path):
    """Verify resetting demo records does not delete real non-demo users or trades."""
    test_db = tmp_path / "test_reset.db"
    init_db(test_db)

    # Insert a real user and trade
    with db_session(test_db) as conn:
        conn.execute(
            """
            INSERT INTO users (id, name, email, password_hash, starting_balance, currency, timezone, is_demo, created_at)
            VALUES ('real_user_01', 'Real Trader', 'real@firm.com', 'hash123', 100000.0, 'USD', 'UTC', 0, '2026-01-01T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO trades (id, user_id, symbol, asset_class, direction, status, is_demo, entry_time, exit_time, entry_price, exit_price, quantity, net_pnl, created_at, updated_at)
            VALUES ('trd_real_01', 'real_user_01', 'EUR/USD', 'Forex', 'LONG', 'CLOSED', 0, '2026-01-01T10:00:00Z', '2026-01-01T12:00:00Z', 1.08, 1.09, 1.0, 1000.0, '2026-01-01T10:00:00Z', '2026-01-01T12:00:00Z')
            """
        )

    # Seed demo data in test_db (with small seed for test)
    # Perform demo reset
    reset_demo_data(test_db)

    # Verify real records are still intact
    with db_session(test_db) as conn:
        real_user = conn.execute("SELECT * FROM users WHERE id = 'real_user_01'").fetchone()
        assert real_user is not None
        assert real_user["is_demo"] == 0

        real_trade = conn.execute("SELECT * FROM trades WHERE id = 'trd_real_01'").fetchone()
        assert real_trade is not None
        assert real_trade["is_demo"] == 0


# ==============================================================================
# 2. STATISTICAL CORRECTNESS TESTS
# ==============================================================================

def test_trade_pnl_formula_long_and_short():
    """Test authoritative gross and net P&L calculations for Long and Short."""
    # Long: EUR/USD standard lot (contract size 100,000)
    # Entry 1.08000, Exit 1.08500 (+50 pips), 2.0 lots -> Gross = 0.00500 * 2.0 * 100,000 = $1,000.00
    # Commission $8.00, Fees $1.00, Swap -$2.50 -> Net = 1000 - 8 - 1 - 2.50 = $988.50
    pnl_long = compute_trade_pnl(
        direction="LONG",
        entry_price=1.08000,
        exit_price=1.08500,
        quantity=2.0,
        contract_size=100000.0,
        commission=8.0,
        other_fees=1.0,
        signed_swap_adjustment=-2.50,
        planned_risk_amount=500.0,
    )
    assert pnl_long["gross_pnl"] == 1000.00
    assert pnl_long["net_pnl"] == 988.50
    assert pnl_long["realized_r_multiple"] == round(988.50 / 500.0, 3)

    # Short: Entry 1.09000, Exit 1.08500 (+50 pips drop), 1.0 lot -> Gross = $500.00
    pnl_short = compute_trade_pnl(
        direction="SHORT",
        entry_price=1.09000,
        exit_price=1.08500,
        quantity=1.0,
        contract_size=100000.0,
        commission=4.0,
        other_fees=0.5,
        signed_swap_adjustment=1.50,  # positive swap adds
        planned_risk_amount=250.0,
    )
    assert pnl_short["gross_pnl"] == 500.00
    assert pnl_short["net_pnl"] == 500.00 - 4.0 - 0.5 + 1.50  # 497.00
    assert pnl_short["realized_r_multiple"] == round(497.00 / 250.0, 3)


def test_win_rate_excludes_breakeven_trades():
    """Verify win rate denominator strictly excludes breakeven trades: wins / (wins + losses) * 100."""
    # 6 wins, 4 losses, 5 breakevens (net_pnl = 0.0)
    mock_trades = [
        {"status": "CLOSED", "exit_time": "2026-01-01T10:00:00Z", "net_pnl": 100.0, "gross_pnl": 100.0} for _ in range(6)
    ] + [
        {"status": "CLOSED", "exit_time": "2026-01-01T11:00:00Z", "net_pnl": -50.0, "gross_pnl": -50.0} for _ in range(4)
    ] + [
        {"status": "CLOSED", "exit_time": "2026-01-01T12:00:00Z", "net_pnl": 0.0, "gross_pnl": 0.0} for _ in range(5)
    ]

    metrics = compute_aggregate_metrics(mock_trades, starting_balance=10000.0)
    assert metrics["total_closed_trades"] == 15
    assert metrics["winning_trades"] == 6
    assert metrics["losing_trades"] == 4
    assert metrics["breakeven_trades"] == 5
    # Win rate should be 6 / (6 + 4) * 100 = 60.0% (NOT 6 / 15 = 40.0%)
    assert metrics["win_rate"] == 60.0


def test_profit_factor_and_undefined_cases():
    """Test profit factor computation and explicit safe handling when there are no losses."""
    # Normal case: pos_sum = $600, neg_sum = -$200 -> PF = 3.0
    mock_trades = [
        {"status": "CLOSED", "exit_time": "2026-01-01T10:00:00Z", "net_pnl": 300.0, "gross_pnl": 300.0},
        {"status": "CLOSED", "exit_time": "2026-01-01T11:00:00Z", "net_pnl": 300.0, "gross_pnl": 300.0},
        {"status": "CLOSED", "exit_time": "2026-01-01T12:00:00Z", "net_pnl": -200.0, "gross_pnl": -200.0},
    ]
    m1 = compute_aggregate_metrics(mock_trades)
    assert m1["profit_factor"] == 3.0

    # No losses case: only winning trades -> PF should be None (not crash with ZeroDivisionError or return NaN)
    mock_win_only = [
        {"status": "CLOSED", "exit_time": "2026-01-01T10:00:00Z", "net_pnl": 150.0, "gross_pnl": 150.0},
    ]
    m2 = compute_aggregate_metrics(mock_win_only)
    assert m2["profit_factor"] is None
    assert m2["winning_trades"] == 1
    assert m2["losing_trades"] == 0


def test_expectancy_and_average_win_loss():
    """Verify expectancy formula: sum(net_pnl) / total_closed_trades (including BE)."""
    # Wins: +200, +100; Losses: -100; Breakeven: 0
    # Total net = 200, total trades = 4 -> Expectancy = 200 / 4 = $50.00
    mock_trades = [
        {"status": "CLOSED", "exit_time": "2026-01-01T10:00:00Z", "net_pnl": 200.0, "gross_pnl": 200.0},
        {"status": "CLOSED", "exit_time": "2026-01-01T11:00:00Z", "net_pnl": 100.0, "gross_pnl": 100.0},
        {"status": "CLOSED", "exit_time": "2026-01-01T12:00:00Z", "net_pnl": -100.0, "gross_pnl": -100.0},
        {"status": "CLOSED", "exit_time": "2026-01-01T13:00:00Z", "net_pnl": 0.0, "gross_pnl": 0.0},
    ]
    metrics = compute_aggregate_metrics(mock_trades)
    assert metrics["expectancy"] == 50.00
    assert metrics["average_win"] == 150.00  # (200 + 100) / 2
    assert metrics["average_loss"] == -100.00  # (-100) / 1
    assert metrics["average_rr_ratio"] == 1.50  # 150 / 100


def test_maximum_drawdown_on_realized_equity_curve():
    """Test peak-to-trough decline on chronologically ordered equity curve."""
    # Starting Balance: $10,000
    # Trade 1: +$2,000 -> Equity $12,000 (HWM: $12,000)
    # Trade 2: -$3,000 -> Equity $9,000  (DD = $3,000, DD% = 3000 / 12000 = 25.0%)
    # Trade 3: +$1,000 -> Equity $10,000 (DD = $2,000)
    # Trade 4: +$4,000 -> Equity $14,000 (HWM: $14,000)
    # Trade 5: -$1,400 -> Equity $12,600 (DD = $1,400, DD% = 1400 / 14000 = 10.0%)
    # Max DD currency should be $3,000, Max DD % should be 25.0%
    mock_trades = [
        {"status": "CLOSED", "exit_time": "2026-01-01T10:00:00Z", "net_pnl": 2000.0, "gross_pnl": 2000.0},
        {"status": "CLOSED", "exit_time": "2026-01-02T10:00:00Z", "net_pnl": -3000.0, "gross_pnl": -3000.0},
        {"status": "CLOSED", "exit_time": "2026-01-03T10:00:00Z", "net_pnl": 1000.0, "gross_pnl": 1000.0},
        {"status": "CLOSED", "exit_time": "2026-01-04T10:00:00Z", "net_pnl": 4000.0, "gross_pnl": 4000.0},
        {"status": "CLOSED", "exit_time": "2026-01-05T10:00:00Z", "net_pnl": -1400.0, "gross_pnl": -1400.0},
    ]
    metrics = compute_aggregate_metrics(mock_trades, starting_balance=10000.0)
    assert metrics["max_drawdown_currency"] == 3000.00
    assert metrics["max_drawdown_pct"] == 25.00


def test_continuous_daily_pnl_series_and_reconciliation():
    """Verify daily P&L returns every calendar day in range and reconciles with total net P&L."""
    start_date = "2026-01-01"
    end_date = "2026-01-05"  # 5 calendar days

    # Trades closed only on Jan 1 and Jan 4
    trades = [
        {"status": "CLOSED", "exit_time": "2026-01-01T14:00:00Z", "net_pnl": 250.0, "gross_pnl": 250.0},
        {"status": "CLOSED", "exit_time": "2026-01-01T16:00:00Z", "net_pnl": 150.0, "gross_pnl": 150.0},
        {"status": "CLOSED", "exit_time": "2026-01-04T10:00:00Z", "net_pnl": -100.0, "gross_pnl": -100.0},
    ]

    series = generate_daily_pnl_series(trades, start_date=start_date, end_date=end_date, timezone_str="UTC")
    assert len(series) == 5  # Jan 1, Jan 2, Jan 3, Jan 4, Jan 5

    # Check zero days are present
    jan2 = next(d for d in series if d["date"] == "2026-01-02")
    assert jan2["net_pnl"] == 0.0
    assert jan2["closed_trades_count"] == 0

    jan3 = next(d for d in series if d["date"] == "2026-01-03")
    assert jan3["net_pnl"] == 0.0
    assert jan3["closed_trades_count"] == 0

    jan1 = next(d for d in series if d["date"] == "2026-01-01")
    assert jan1["net_pnl"] == 400.0
    assert jan1["closed_trades_count"] == 2

    # Reconcile sum of daily net P&L with closed trades total
    daily_sum = sum(d["net_pnl"] for d in series)
    total_trades_net = sum(t["net_pnl"] for t in trades)
    assert round(daily_sum, 2) == round(total_trades_net, 2) == 300.00


def test_empty_trade_history_handles_safely():
    """Verify empty trade histories return safe defaults and do not raise exceptions."""
    metrics = compute_aggregate_metrics([], starting_balance=50000.0)
    assert metrics["total_closed_trades"] == 0
    assert metrics["win_rate"] is None
    assert metrics["profit_factor"] is None
    assert metrics["net_pnl"] == 0.0
    assert metrics["current_equity"] == 50000.0


# ==============================================================================
# 3. USER ISOLATION AND API SECURITY TESTS
# ==============================================================================

def test_user_data_isolation_between_trader_01_and_trader_02(api_client):
    """Verify Demo Trader 01 cannot view or modify Demo Trader 02's records."""
    # Query trades as Demo Trader 01
    resp1 = api_client.get("/api/v1/trades?page_size=10", headers={"X-User-Id": "demo_trader_01"})
    assert resp1.status_code == 200
    trades1 = resp1.json()["items"]
    assert len(trades1) > 0
    for t in trades1:
        assert t["user_id"] == "demo_trader_01"

    # Query trades as Demo Trader 02
    resp2 = api_client.get("/api/v1/trades?page_size=10", headers={"X-User-Id": "demo_trader_02"})
    assert resp2.status_code == 200
    trades2 = resp2.json()["items"]
    assert len(trades2) > 0
    for t in trades2:
        assert t["user_id"] == "demo_trader_02"

    # Grab a trade ID from Trader 02
    trader_02_trade_id = trades2[0]["id"]

    # Attempt to retrieve Trader 02's trade while authenticated as Trader 01 -> must be 404
    cross_get = api_client.get(f"/api/v1/trades/{trader_02_trade_id}", headers={"X-User-Id": "demo_trader_01"})
    assert cross_get.status_code == 404

    # Attempt to modify Trader 02's trade as Trader 01 -> must be 404
    cross_put = api_client.put(
        f"/api/v1/trades/{trader_02_trade_id}",
        json={"notes": "Hacked notes"},
        headers={"X-User-Id": "demo_trader_01"},
    )
    assert cross_put.status_code == 404

    # Attempt to delete Trader 02's trade as Trader 01 -> must be 404
    cross_del = api_client.delete(f"/api/v1/trades/{trader_02_trade_id}", headers={"X-User-Id": "demo_trader_01"})
    assert cross_del.status_code == 404


def test_csv_export_isolation(api_client):
    """Verify CSV export strictly contains only the requesting user's records."""
    resp = api_client.get("/api/v1/trades/export/csv", headers={"X-User-Id": "demo_trader_03"})
    assert resp.status_code == 200
    csv_text = resp.text
    lines = csv_text.strip().split("\n")
    assert len(lines) > 1  # header + data lines

    header = lines[0].split(",")
    user_id_idx = header.index("user_id")

    for line in lines[1:50]:  # sample first 50 exported lines
        cols = line.split(",")
        assert cols[user_id_idx] == "demo_trader_03", f"Leaked trade from other user: {line}"


def test_crud_trade_lifecycle(api_client):
    """Test full create, read, update, delete trade cycle."""
    user_id = "demo_trader_01"

    # Create new trade
    new_trade_data = {
        "symbol": "GBP/USD",
        "asset_class": "Forex",
        "direction": "LONG",
        "status": "CLOSED",
        "is_demo": True,
        "entry_time": "2026-10-24T10:00:00Z",
        "exit_time": "2026-10-24T12:00:00Z",
        "entry_price": 1.29000,
        "exit_price": 1.29500,
        "quantity": 1.5,
        "contract_size": 100000.0,
        "commission": 6.0,
        "other_fees": 0.5,
        "signed_swap_adjustment": 0.0,
        "planned_risk_amount": 300.0,
        "strategy_or_setup": "Test Setup",
        "trading_session": "London",
    }
    create_res = api_client.post("/api/v1/trades", json=new_trade_data, headers={"X-User-Id": user_id})
    assert create_res.status_code == 201
    created_trade = create_res.json()
    t_id = created_trade["id"]

    # Verify gross and net pnl: 0.00500 * 1.5 * 100,000 = $750.00 gross; net = 750 - 6.5 = $743.50
    assert created_trade["gross_pnl"] == 750.00
    assert created_trade["net_pnl"] == 743.50

    # Retrieve trade
    get_res = api_client.get(f"/api/v1/trades/{t_id}", headers={"X-User-Id": user_id})
    assert get_res.status_code == 200
    assert get_res.json()["id"] == t_id

    # Update trade (modify exit price)
    update_res = api_client.put(
        f"/api/v1/trades/{t_id}",
        json={"exit_price": 1.29600, "notes": "Updated exit higher"},
        headers={"X-User-Id": user_id},
    )
    assert update_res.status_code == 200
    updated_trade = update_res.json()
    # Gross: 0.00600 * 1.5 * 100,000 = $900.00; net = 900 - 6.5 = $893.50
    assert updated_trade["gross_pnl"] == 900.00
    assert updated_trade["net_pnl"] == 893.50
    assert updated_trade["notes"] == "Updated exit higher"

    # Delete trade
    del_res = api_client.delete(f"/api/v1/trades/{t_id}", headers={"X-User-Id": user_id})
    assert del_res.status_code == 200

    # Verify deletion
    verify_del = api_client.get(f"/api/v1/trades/{t_id}", headers={"X-User-Id": user_id})
    assert verify_del.status_code == 404


def test_validation_rejects_exit_before_entry(api_client):
    """Verify backend input validation rejects exit_time preceding entry_time on creation."""
    invalid_trade = {
        "symbol": "EUR/USD",
        "direction": "LONG",
        "status": "CLOSED",
        "entry_time": "2026-10-24T12:00:00Z",
        "exit_time": "2026-10-24T10:00:00Z",  # precedes entry!
        "entry_price": 1.08,
        "exit_price": 1.09,
        "quantity": 1.0,
    }
    res = api_client.post("/api/v1/trades", json=invalid_trade, headers={"X-User-Id": "demo_trader_01"})
    assert res.status_code == 422  # Validation error


def test_update_trade_validation_rejects_exit_before_entry(api_client):
    """Verify backend input validation rejects invalid exit_time on update and does not corrupt DB."""
    # First create a valid trade
    valid_trade = {
        "symbol": "EUR/USD",
        "direction": "LONG",
        "status": "CLOSED",
        "entry_time": "2026-10-24T12:00:00Z",
        "exit_time": "2026-10-24T14:00:00Z",
        "entry_price": 1.0800,
        "exit_price": 1.0850,
        "quantity": 1.0,
        "commission": 5.0,
    }
    create_res = api_client.post("/api/v1/trades", json=valid_trade, headers={"X-User-Id": "demo_trader_01"})
    assert create_res.status_code == 201
    trade_id = create_res.json()["id"]

    try:
        # Attempt update with exit_time before entry_time
        update_res = api_client.put(
            f"/api/v1/trades/{trade_id}",
            json={"exit_time": "2026-10-24T11:00:00Z"},
            headers={"X-User-Id": "demo_trader_01"},
        )
        assert update_res.status_code == 422
        assert "precede" in update_res.json()["detail"].lower()

        # Verify DB trade record remains intact and uncorrupted
        get_res = api_client.get(f"/api/v1/trades/{trade_id}", headers={"X-User-Id": "demo_trader_01"})
        assert get_res.status_code == 200
        assert get_res.json()["exit_time"] == "2026-10-24T14:00:00Z"
    finally:
        # Cleanup
        api_client.delete(f"/api/v1/trades/{trade_id}", headers={"X-User-Id": "demo_trader_01"})


def test_invalid_user_id_returns_401(api_client):
    """Verify that specifying a non-existent X-User-Id returns 401 instead of silent fallback."""
    res = api_client.get("/api/v1/trades", headers={"X-User-Id": "non_existent_hacker_user"})
    assert res.status_code == 401
    assert "Invalid user" in res.json()["detail"]


def test_csv_injection_defense(api_client):
    """Verify formula injection characters (=, +, -, @) are sanitized with leading single quote."""
    trade_payload = {
        "symbol": "=1+2",
        "direction": "LONG",
        "status": "CLOSED",
        "entry_time": "2026-10-24T10:00:00Z",
        "exit_time": "2026-10-24T11:00:00Z",
        "entry_price": 1.0800,
        "exit_price": 1.0850,
        "quantity": 1.0,
        "notes": "=SUM(A1:A10)",
        "strategy_or_setup": "+cmd|'/C calc'!A0",
    }
    create_res = api_client.post("/api/v1/trades", json=trade_payload, headers={"X-User-Id": "demo_trader_01"})
    assert create_res.status_code == 201
    trade_id = create_res.json()["id"]

    try:
        csv_res = api_client.get("/api/v1/trades/export/csv", headers={"X-User-Id": "demo_trader_01"})
        assert csv_res.status_code == 200
        content = csv_res.text
        # Must contain sanitized versions
        assert "'=SUM(A1:A10)" in content
        assert "'+cmd|'/C calc'!A0" in content
    finally:
        api_client.delete(f"/api/v1/trades/{trade_id}", headers={"X-User-Id": "demo_trader_01"})


def test_timezone_normalization_handling(api_client):
    """Verify timestamps with non-UTC timezone offsets are accepted, parsed and normalized."""
    trade_payload = {
        "symbol": "USD/CAD",
        "direction": "SHORT",
        "status": "CLOSED",
        "entry_time": "2026-10-24T15:00:00+02:00",
        "exit_time": "2026-10-24T17:30:00+02:00",
        "entry_price": 1.3500,
        "exit_price": 1.3450,
        "quantity": 1.0,
    }
    create_res = api_client.post("/api/v1/trades", json=trade_payload, headers={"X-User-Id": "demo_trader_01"})
    assert create_res.status_code == 201
    trade_data = create_res.json()
    trade_id = trade_data["id"]

    try:
        assert trade_data["status"] == "CLOSED"
        assert trade_data["entry_time"] is not None
        assert trade_data["exit_time"] is not None
    finally:
        api_client.delete(f"/api/v1/trades/{trade_id}", headers={"X-User-Id": "demo_trader_01"})



# ==============================================================================
# 4. HIGH-PERFORMANCE BENCHMARK TESTS ON 100,000 DATASET
# ==============================================================================

def test_performance_paginated_query_speed():
    """Verify paginated trade history query executes in under 25ms on indexed SQLite."""
    t0 = time.perf_counter()
    res = list_trades_paginated(
        user_id="demo_trader_01",
        page=1,
        page_size=25,
        sort_by="exit_time",
        sort_order="desc",
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(res["items"]) == 25
    assert res["total"] >= 10_000
    # Must be blazing fast (< 50ms)
    assert elapsed_ms < 50.0, f"Paginated query took too long: {elapsed_ms:.2f}ms"


def test_performance_analytics_overview_speed(api_client):
    """Verify calculating analytics overview across a trader's 10,000 trades executes in under 150ms."""
    t0 = time.perf_counter()
    resp = api_client.get("/api/v1/analytics/overview?range_preset=all", headers={"X-User-Id": "demo_trader_01"})
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert resp.status_code == 200
    metrics = resp.json()
    assert metrics["total_closed_trades"] >= 10_000
    # Must be under 150ms
    assert elapsed_ms < 150.0, f"Analytics overview query took too long: {elapsed_ms:.2f}ms"


def test_admin_health_endpoint(api_client):
    """Verify admin health check endpoint verifies all 100,000 demo trades."""
    resp = api_client.get("/api/v1/admin/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_demo_users"] == 10
    assert data["total_seeded_trades"] == 100_000
    assert data["total_closed_seeded_trades"] == 100_000
    assert data["is_healthy"] is True
    assert all(data["checks"].values())


def test_demo_user_switching_endpoint(api_client):
    """Verify switching active demo user changes context cleanly."""
    resp = api_client.post("/api/v1/auth/switch-demo/demo_trader_05")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["active_user_id"] == "demo_trader_05"

    # Profile check with switched user
    me = api_client.get("/api/v1/auth/me", headers={"X-User-Id": "demo_trader_05"})
    assert me.status_code == 200
    assert me.json()["id"] == "demo_trader_05"


def test_analytics_breakdown_overall(api_client):
    """Verify analytics breakdown endpoint supports 'overall' grouping."""
    resp = api_client.get("/api/v1/analytics/breakdown?group_by=overall", headers={"X-User-Id": "demo_trader_01"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    assert item["key"] == "Overall Performance"
    assert item["trade_count"] >= 10_000
    assert item["winning_trades"] > 0
    assert item["losing_trades"] > 0
    assert item["win_rate"] is not None
    assert item["gross_profit"] is not None and item["gross_profit"] > 0
    assert item["gross_loss"] is not None and item["gross_loss"] > 0
    assert item["net_pnl"] != 0
    assert item["profit_factor"] is not None


def test_analytics_breakdown_session(api_client):
    """Verify analytics breakdown endpoint supports 'session' grouping."""
    resp = api_client.get("/api/v1/analytics/breakdown?group_by=session", headers={"X-User-Id": "demo_trader_01"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    keys = {d["key"] for d in data}
    assert "London" in keys
    assert "New York" in keys
