from __future__ import annotations

import math
import os
import random
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import db

SEED = 20261023
REFERENCE_END = date(2026, 10, 23)
TRADER_COUNT = 10
TRADES_PER_TRADER = 10_000
YEARS = 3
INSTRUMENTS = {
    "EURUSD": (1.08, 100_000, 5, 0.0030),
    "GBPUSD": (1.27, 100_000, 5, 0.0040),
    "AUDUSD": (0.66, 100_000, 5, 0.0025),
    "NZDUSD": (0.61, 100_000, 5, 0.0025),
    "XAUUSD": (2300, 100, 2, 18.0),
    "US30": (38000, 1, 1, 220.0),
}
SETUPS = ("Breakout", "Pullback", "Range Fade", "News Momentum", "Trend Continuation", "Reversal")
ACCOUNT_TIMEZONES = (
    "America/New_York", "Europe/London", "Asia/Kolkata", "Australia/Sydney",
)
UTC = timezone.utc


def generate_trader(
    index: int,
    trade_count: int,
    end_date: date = REFERENCE_END,
    seed: int = SEED,
    years: int = YEARS,
) -> tuple[dict, list[dict]]:
    rng = random.Random(f"{seed}-{index}")
    user_id = f"demo_{index:02d}"
    balance = rng.choice((25_000, 50_000, 100_000, 150_000, 250_000))
    size_scale = balance / 100_000
    baseline_win_rate = rng.uniform(0.42, 0.56)
    reward_to_risk = rng.uniform(1.2, 1.9)
    setup_bias = {setup: rng.uniform(-0.08, 0.08) for setup in SETUPS}
    start_date = end_date - timedelta(days=365 * years)
    trading_days = [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
        if (start_date + timedelta(days=offset)).weekday() < 5
    ]
    if trade_count and not trading_days:
        raise ValueError("demo date range must include at least one weekday")
    weights = [rng.lognormvariate(0, 0.5) for _ in trading_days]
    for _ in range(7):
        if not trading_days:
            break
        index_start = rng.randrange(len(trading_days))
        quiet_length = rng.randint(8, 20)
        for position in range(index_start, min(index_start + quiet_length, len(trading_days))):
            weights[position] *= 0.05

    slots = []
    for day_index in rng.choices(range(len(trading_days)), weights=weights, k=trade_count):
        segment = rng.random()
        hour = rng.randint(0, 6) if segment < 0.2 else rng.randint(7, 12) if segment < 0.6 else rng.randint(13, 20)
        slots.append((trading_days[day_index], hour, rng.randrange(60), rng.randrange(60)))
    slots.sort()

    trades: list[dict] = []
    regime, regime_remaining = 0.0, rng.randint(150, 400)
    for trade_index, (day, hour, minute, second) in enumerate(slots):
        if regime_remaining == 0:
            regime, regime_remaining = rng.choice((-0.12, 0, 0, 0.08)), rng.randint(150, 400)
        regime_remaining -= 1
        instrument = rng.choice(tuple(INSTRUMENTS))
        reference_price, contract_size, decimals, adverse_move = INSTRUMENTS[instrument]
        setup = rng.choice(SETUPS)
        followed_rules = rng.random() < 0.82
        rule_adhered = None if rng.random() < 0.10 else int(followed_rules)
        win_rate = min(
            0.85,
            max(0.15, baseline_win_rate + regime + setup_bias[setup] - (0 if followed_rules else 0.07)),
        )
        direction = rng.choice((1, -1))
        quantity = round(max(0.01, rng.lognormvariate(math.log(0.4 * size_scale), 0.5)), 2)
        entry = round(reference_price * rng.uniform(0.94, 1.06), decimals)
        opened_at = datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=UTC)
        closed_at = opened_at + timedelta(
            minutes=max(1, min(int(rng.lognormvariate(math.log(75), 1.1)), 2880))
        )
        if closed_at.weekday() >= 5 or closed_at.date() > end_date:
            closed_at = opened_at + timedelta(minutes=rng.randint(5, 60))

        scratch = rng.random() < 0.025
        is_winner = rng.random() < win_rate
        loss_size = adverse_move * rng.uniform(0.5, 1.3)
        move_size = loss_size * reward_to_risk * rng.uniform(0.6, 1.5) if is_winner else loss_size
        if rng.random() < 0.01:
            move_size *= 4
        exit_price = entry if scratch else round(
            entry + direction * (move_size if is_winner else -move_size), decimals
        )
        gross = round((exit_price - entry) * direction * quantity * contract_size, 2)
        if scratch:
            commission = fees = slippage = swap = 0.0
        else:
            nights = (closed_at.date() - opened_at.date()).days
            commission = round(quantity * rng.uniform(5, 8), 2)
            fees = round(quantity * rng.uniform(0.2, 0.8), 2)
            slippage = round(quantity * rng.uniform(0, 2.5), 2)
            swap = round(quantity * nights * rng.uniform(-3.5, 1), 2)
        trades.append({
            "id": f"{user_id}-{trade_index + 1:05d}",
            "user_id": user_id,
            "instrument": instrument,
            "direction": direction,
            "qty": quantity,
            "entry": entry,
            "exit": exit_price,
            "contract_size": contract_size,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "setup": setup,
            "gross": gross,
            "commission": commission,
            "fees": fees,
            "slippage": slippage,
            "swap": swap,
            "rule_adhered": rule_adhered,
        })

    account_timezone = ACCOUNT_TIMEZONES[(index - 1) % len(ACCOUNT_TIMEZONES)]
    local_end = max(
        (trade["closed_at"].astimezone(ZoneInfo(account_timezone)).date() for trade in trades),
        default=end_date,
    )
    account = {
        "user_id": user_id,
        "name": f"DEMO Trader {index:02d} (synthetic)",
        "currency": "USD",
        "start_balance": float(balance),
        "tz": account_timezone,
        "is_demo": 1,
        "data_end": local_end.isoformat(),
    }
    return account, trades


def _seed(connection: sqlite3.Connection, count: int, seed: int) -> int:
    if os.getenv("APP_ENV", "").lower() == "production":
        raise RuntimeError("Demo trade seeding is disabled when APP_ENV=production")

    base_count, remainder = divmod(count, TRADER_COUNT)
    with connection:
        for index in range(1, TRADER_COUNT + 1):
            trade_count = base_count + (1 if index <= remainder else 0)
            account, trades = generate_trader(index, trade_count, seed=seed)
            existing = connection.execute(
                "SELECT is_demo FROM accounts WHERE user_id = ?",
                (account["user_id"],),
            ).fetchone()
            if existing and not existing["is_demo"]:
                raise RuntimeError(
                    f"{account['user_id']} is a real account; refusing to modify it"
                )

            connection.execute(
                "DELETE FROM trades WHERE user_id = ? AND is_demo = 1",
                (account["user_id"],),
            )
            connection.execute(
                """INSERT INTO accounts
                   (user_id, name, currency, start_balance, tz, is_demo, data_end)
                   VALUES (:user_id, :name, :currency, :start_balance, :tz, :is_demo, :data_end)
                   ON CONFLICT(user_id) DO UPDATE SET
                     name=excluded.name, currency=excluded.currency,
                     start_balance=excluded.start_balance, tz=excluded.tz,
                     is_demo=excluded.is_demo, data_end=excluded.data_end""",
                account,
            )
            db.insert_trades(connection, trades, account["tz"], True)

    return int(connection.execute(
        "SELECT COUNT(*) FROM trades WHERE is_demo = 1"
    ).fetchone()[0])


def seed_demo_trades(
    database_path: str | Path,
    count: int = 100_000,
    *,
    seed: int = SEED,
) -> int:
    if count < 0:
        raise ValueError("demo trade count cannot be negative")
    connection = db.connect(database_path)
    try:
        db.init_db(connection)
        return _seed(connection, count, seed)
    finally:
        connection.close()


def initialize_database(database_path: str | Path) -> None:
    connection = db.connect(database_path)
    try:
        db.init_db(connection)
    finally:
        connection.close()
