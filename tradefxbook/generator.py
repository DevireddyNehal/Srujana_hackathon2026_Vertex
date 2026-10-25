"""
TradeFXBook Deterministic Demo Data Generator.
Generates exactly 10 demo users and exactly 10,000 closed trades per user (100,000 total).
Guarantees deterministic reproducibility (seed=42), idempotency, and distinct trader profiles.
"""

import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import zoneinfo

from tradefxbook.config import settings
from tradefxbook.database import db_session, init_db
from tradefxbook.calculations import compute_trade_pnl


def hash_password(password: str) -> str:
    """Deterministic, secure PBKDF2 password hasher."""
    salt = settings.DEMO_PASSWORD_SALT.encode("utf-8")
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return pwd_hash.hex()


TRADER_PROFILES: List[Dict[str, Any]] = [
    {
        "id": "demo_trader_01",
        "name": "Demo Trader 01",
        "email": "demo.trader01@tradefxbook.demo",
        "starting_balance": 50000.0,
        "currency": "USD",
        "timezone": "America/New_York",
        "style": "Conservative Swing Trader",
        "profile_description": "Discipline-first macro swing trader focusing on EUR/USD and GBP/USD with tight risk controls.",
        "win_rate_target": 0.62,
        "breakeven_rate": 0.02,
        "symbols": [("EUR/USD", "Forex", 100000.0, 1.0850), ("GBP/USD", "Forex", 100000.0, 1.2950)],
        "sessions": ["London", "New York", "London/NY Overlap"],
        "setups": ["Order Block / FVG", "Trend Pullback", "Daily Range Liquidity"],
        "base_lot_min": 1.0,
        "base_lot_max": 2.5,
        "rr_target_min": 1.4,
        "rr_target_max": 2.2,
        "avg_hold_minutes": 720,  # 12 hours
    },
    {
        "id": "demo_trader_02",
        "name": "Demo Trader 02",
        "email": "demo.trader02@tradefxbook.demo",
        "starting_balance": 25000.0,
        "currency": "USD",
        "timezone": "Europe/London",
        "style": "High-Frequency Scalper",
        "profile_description": "Fast-paced intraday scalper targeting 5-15 pip expansions on EUR/USD and USD/JPY.",
        "win_rate_target": 0.52,
        "breakeven_rate": 0.03,
        "symbols": [("EUR/USD", "Forex", 100000.0, 1.0820), ("USD/JPY", "Forex", 100000.0, 152.40)],
        "sessions": ["London", "New York"],
        "setups": ["1m/5m FVG Tap", "Orderflow Delta Imbalance", "VWAP Rejection"],
        "base_lot_min": 0.5,
        "base_lot_max": 1.5,
        "rr_target_min": 1.1,
        "rr_target_max": 1.6,
        "avg_hold_minutes": 25,
    },
    {
        "id": "demo_trader_03",
        "name": "Demo Trader 03",
        "email": "demo.trader03@tradefxbook.demo",
        "starting_balance": 100000.0,
        "currency": "USD",
        "timezone": "America/Chicago",
        "style": "Trend Follower & Index Runner",
        "profile_description": "Patient momentum trend follower running big asymmetric R:R positions on US30 and Gold.",
        "win_rate_target": 0.43,
        "breakeven_rate": 0.02,
        "symbols": [("US30", "Indices", 1.0, 42500.0), ("XAU/USD", "Commodity", 100.0, 2680.0)],
        "sessions": ["New York", "London/NY Overlap"],
        "setups": ["4H Trend Continuation", "Breakout Pullback", "Structure Shift"],
        "base_lot_min": 2.0,
        "base_lot_max": 5.0,
        "rr_target_min": 2.2,
        "rr_target_max": 3.8,
        "avg_hold_minutes": 1440,  # 24 hours
    },
    {
        "id": "demo_trader_04",
        "name": "Demo Trader 04",
        "email": "demo.trader04@tradefxbook.demo",
        "starting_balance": 50000.0,
        "currency": "USD",
        "timezone": "Europe/London",
        "style": "Breakout Specialist",
        "profile_description": "London session open breakout trader hunting momentum continuation after consolidation.",
        "win_rate_target": 0.49,
        "breakeven_rate": 0.02,
        "symbols": [("GBP/USD", "Forex", 100000.0, 1.2980), ("EUR/USD", "Forex", 100000.0, 1.0860)],
        "sessions": ["London"],
        "setups": ["London Open Breakout", "Asian Range Sweep", "High Volume Impulses"],
        "base_lot_min": 1.0,
        "base_lot_max": 3.0,
        "rr_target_min": 1.5,
        "rr_target_max": 2.5,
        "avg_hold_minutes": 180,
    },
    {
        "id": "demo_trader_05",
        "name": "Demo Trader 05",
        "email": "demo.trader05@tradefxbook.demo",
        "starting_balance": 30000.0,
        "currency": "USD",
        "timezone": "Asia/Tokyo",
        "style": "Mean Reversion Range Trader",
        "profile_description": "Asian session range-bound specialist trading boundaries on USD/JPY and AUD/USD.",
        "win_rate_target": 0.66,
        "breakeven_rate": 0.025,
        "symbols": [("USD/JPY", "Forex", 100000.0, 151.80), ("AUD/USD", "Forex", 100000.0, 0.6620)],
        "sessions": ["Asian"],
        "setups": ["Asian Range Boundary", "Bollinger Band Reversion", "Support/Resistance Bounce"],
        "base_lot_min": 0.8,
        "base_lot_max": 2.0,
        "rr_target_min": 0.9,
        "rr_target_max": 1.4,
        "avg_hold_minutes": 240,
    },
    {
        "id": "demo_trader_06",
        "name": "Demo Trader 06",
        "email": "demo.trader06@tradefxbook.demo",
        "starting_balance": 20000.0,
        "currency": "USD",
        "timezone": "America/Los_Angeles",
        "style": "Crypto & Momentum Trader",
        "profile_description": "Aggressive crypto trader capturing volatility expansions on BTC/USD.",
        "win_rate_target": 0.45,
        "breakeven_rate": 0.02,
        "symbols": [("BTC/USD", "Crypto", 1.0, 68000.0), ("ETH/USD", "Crypto", 1.0, 2600.0)],
        "sessions": ["New York", "Asian"],
        "setups": ["Liquidity Grab & Reclaim", "Bull/Bear Flag Breakout", "EMA Momentum Cross"],
        "base_lot_min": 0.2,
        "base_lot_max": 1.0,
        "rr_target_min": 1.8,
        "rr_target_max": 3.2,
        "avg_hold_minutes": 360,
    },
    {
        "id": "demo_trader_07",
        "name": "Demo Trader 07",
        "email": "demo.trader07@tradefxbook.demo",
        "starting_balance": 50000.0,
        "currency": "USD",
        "timezone": "America/New_York",
        "style": "Emotional / Inconsistent Trader",
        "profile_description": "Struggles with FOMO and revenge trading, showing irregular lot sizes and negative expectancy.",
        "win_rate_target": 0.38,
        "breakeven_rate": 0.02,
        "symbols": [("XAU/USD", "Commodity", 100.0, 2650.0), ("US30", "Indices", 1.0, 42000.0)],
        "sessions": ["New York", "London/NY Overlap"],
        "setups": ["Chasing Green Candles", "Impulse Entry", "Counter-trend Hope"],
        "base_lot_min": 0.5,
        "base_lot_max": 6.0,  # wide erratic sizing
        "rr_target_min": 0.8,
        "rr_target_max": 1.5,
        "avg_hold_minutes": 90,
    },
    {
        "id": "demo_trader_08",
        "name": "Demo Trader 08",
        "email": "demo.trader08@tradefxbook.demo",
        "starting_balance": 250000.0,
        "currency": "USD",
        "timezone": "Europe/Zurich",
        "style": "Institutional Systematic Trader",
        "profile_description": "Strict rule-based portfolio trader across Forex majors and Gold with low drawdown.",
        "win_rate_target": 0.57,
        "breakeven_rate": 0.02,
        "symbols": [("EUR/USD", "Forex", 100000.0, 1.0850), ("XAU/USD", "Commodity", 100.0, 2690.0)],
        "sessions": ["London", "New York"],
        "setups": ["Institutional Order Flow", "Fair Value Gap", "Liquidity Sweep Model"],
        "base_lot_min": 3.0,
        "base_lot_max": 7.0,
        "rr_target_min": 1.6,
        "rr_target_max": 2.4,
        "avg_hold_minutes": 540,
    },
    {
        "id": "demo_trader_09",
        "name": "Demo Trader 09",
        "email": "demo.trader09@tradefxbook.demo",
        "starting_balance": 40000.0,
        "currency": "USD",
        "timezone": "America/New_York",
        "style": "News Event Volatility Trader",
        "profile_description": "Trades high-impact economic releases (CPI, NFP, FOMC) with wide spreads and fast resolution.",
        "win_rate_target": 0.50,
        "breakeven_rate": 0.02,
        "symbols": [("GBP/USD", "Forex", 100000.0, 1.2940), ("US30", "Indices", 1.0, 42300.0)],
        "sessions": ["New York"],
        "setups": ["NFP Straddle Breakout", "CPI Reaction Fade", "Fed Decision Momentum"],
        "base_lot_min": 1.0,
        "base_lot_max": 3.0,
        "rr_target_min": 1.4,
        "rr_target_max": 2.8,
        "avg_hold_minutes": 45,
    },
    {
        "id": "demo_trader_10",
        "name": "Demo Trader 10",
        "email": "demo.trader10@tradefxbook.demo",
        "starting_balance": 60000.0,
        "currency": "USD",
        "timezone": "Asia/Singapore",
        "style": "Algorithmic Grid/Session Trader",
        "profile_description": "Automated session strategy taking high-probability tactical edges with strict stop loss.",
        "win_rate_target": 0.60,
        "breakeven_rate": 0.025,
        "symbols": [("EUR/USD", "Forex", 100000.0, 1.0840), ("USD/JPY", "Forex", 100000.0, 152.00)],
        "sessions": ["Asian", "London"],
        "setups": ["Algo Session Sweep", "Mean Reversion Pivot", "Volatility Squeeze Breakout"],
        "base_lot_min": 1.0,
        "base_lot_max": 2.2,
        "rr_target_min": 1.2,
        "rr_target_max": 1.8,
        "avg_hold_minutes": 150,
    },
]


def check_demo_dataset_status(db_path: Optional[Any] = None) -> Dict[str, Any]:
    """
    Checks if the demo dataset is already seeded in the database.
    """
    with db_session(db_path) as conn:
        user_row = conn.execute(
            "SELECT COUNT(*) as count FROM users WHERE is_demo = 1 AND id LIKE 'demo_trader_%'"
        ).fetchone()
        demo_user_count = user_row["count"] if user_row else 0

        trade_row = conn.execute(
            "SELECT COUNT(*) as count FROM trades WHERE is_demo = 1 AND seed_batch = ?",
            (settings.DEMO_SEED_BATCH,),
        ).fetchone()
        demo_trade_count = trade_row["count"] if trade_row else 0

        closed_row = conn.execute(
            "SELECT COUNT(*) as count FROM trades WHERE is_demo = 1 AND seed_batch = ? AND status = 'CLOSED'",
            (settings.DEMO_SEED_BATCH,),
        ).fetchone()
        closed_count = closed_row["count"] if closed_row else 0

        # Query counts per user
        trades_per_user = {}
        rows = conn.execute(
            "SELECT user_id, COUNT(*) as cnt FROM trades WHERE is_demo = 1 AND seed_batch = ? GROUP BY user_id ORDER BY user_id",
            (settings.DEMO_SEED_BATCH,),
        ).fetchall()
        for r in rows:
            trades_per_user[r["user_id"]] = r["cnt"]

        is_complete = (
            demo_user_count == settings.DEMO_USERS_COUNT
            and demo_trade_count == settings.TOTAL_DEMO_TRADES
            and closed_count == settings.TOTAL_DEMO_TRADES
            and all(cnt == settings.DEMO_TRADES_PER_USER for cnt in trades_per_user.values())
        )

        return {
            "demo_users_count": demo_user_count,
            "demo_trades_count": demo_trade_count,
            "closed_demo_trades_count": closed_count,
            "trades_per_user": trades_per_user,
            "seed_batch": settings.DEMO_SEED_BATCH,
            "is_complete": is_complete,
        }


def reset_demo_data(db_path: Optional[Any] = None) -> Dict[str, Any]:
    """
    Safely resets ONLY demo data, strictly preserving any non-demo users and trades.
    """
    init_db(db_path)
    with db_session(db_path) as conn:
        # Delete demo trades
        del_trades = conn.execute(
            "DELETE FROM trades WHERE is_demo = 1 OR seed_batch = ?",
            (settings.DEMO_SEED_BATCH,),
        ).rowcount

        # Delete demo users
        del_users = conn.execute(
            "DELETE FROM users WHERE is_demo = 1 AND id LIKE 'demo_trader_%'"
        ).rowcount

        return {
            "deleted_demo_users": del_users,
            "deleted_demo_trades": del_trades,
            "status": "Demo data safely removed. Real non-demo records were untouched.",
        }


def seed_demo_dataset(
    db_path: Optional[Any] = None,
    force_reseed: bool = False,
    custom_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Seeds exactly 10 demo users and exactly 10,000 closed trades per user (100,000 total).
    Deterministic via fixed random seed (default=42).
    Idempotent: will not duplicate if already seeded unless force_reseed=True.
    """
    init_db(db_path)

    # Check existing dataset
    status = check_demo_dataset_status(db_path)
    if status["is_complete"] and not force_reseed:
        return {
            "status": "ALREADY_SEEDED",
            "message": "Demo dataset is already completely seeded with exactly 10 users and 100,000 trades.",
            "demo_users_count": status["demo_users_count"],
            "demo_trades_count": status["demo_trades_count"],
            "closed_demo_trades_count": status["closed_demo_trades_count"],
            "trades_per_user": status["trades_per_user"],
            "seed_batch": settings.DEMO_SEED_BATCH,
        }

    if force_reseed:
        reset_demo_data(db_path)

    # Setup deterministic random generator
    seed_val = custom_seed if custom_seed is not None else settings.RANDOM_SEED
    rng = random.Random(seed_val)

    # Deterministic reference timeline
    ref_end_dt = datetime.fromisoformat(settings.REFERENCE_END_DATE.replace("Z", "+00:00"))
    history_span_seconds = settings.DEMO_HISTORY_DAYS * 86400
    ref_start_dt = ref_end_dt - timedelta(days=settings.DEMO_HISTORY_DAYS)

    users_to_insert = []
    default_password_hash = hash_password("DemoTrader2026!")

    for profile in TRADER_PROFILES:
        users_to_insert.append(
            (
                profile["id"],
                profile["name"],
                profile["email"],
                default_password_hash,
                profile["starting_balance"],
                profile["currency"],
                profile["timezone"],
                1,  # is_demo = True
                profile["profile_description"],
                ref_start_dt.isoformat(),
            )
        )

    # Insert users
    with db_session(db_path) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO users (
                id, name, email, password_hash, starting_balance, currency,
                timezone, is_demo, profile_description, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            users_to_insert,
        )

    # Generate trades for each trader
    total_trades_generated = 0
    trade_insert_sql = """
    INSERT INTO trades (
        id, user_id, symbol, asset_class, direction, status, is_demo,
        entry_time, exit_time, entry_price, exit_price, quantity,
        contract_size, account_currency, stop_loss_price, take_profit_price,
        planned_risk_amount, risk_pct_balance, planned_rr_ratio, realized_r_multiple,
        gross_pnl, commission, other_fees, signed_swap_adjustment, net_pnl,
        strategy_or_setup, trading_session, tags, notes, emotional_state,
        plan_followed, mistakes_or_lessons, seed_batch, created_at, updated_at
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?
    )
    """

    emotional_states = ["Disciplined", "Calm", "Confident", "Focused", "Patient"]
    erratic_states = ["FOMO", "Anxious", "Revenge", "Impatient", "Frustrated"]

    notes_templates = [
        "Clean market structure break on 15m. Followed plan.",
        "Liquidity pool swept prior to session open. Target hit.",
        "Entered on second retest of order block.",
        "High momentum candle exit at predefined take profit.",
        "Trailing stop hit after partial profit secure.",
        "Consolidation exit before major news event.",
        "Technical bounce off confluence level.",
        "Standard execution conforming to playbook criteria.",
    ]

    with db_session(db_path) as conn:
        for profile in TRADER_PROFILES:
            u_id = profile["id"]
            trades_batch = []

            # Generate 10,000 distinct exit timestamps across the history span
            # Generate sorted relative time offsets
            offsets = sorted(rng.randint(3600, history_span_seconds) for _ in range(settings.DEMO_TRADES_PER_USER))

            for trade_idx in range(settings.DEMO_TRADES_PER_USER):
                trade_num = trade_idx + 1
                trade_id = f"trd_{u_id}_{trade_num:05d}"

                # Symbol selection
                sym_info = rng.choice(profile["symbols"])
                symbol, asset_class, contract_size, base_price = sym_info

                direction = "LONG" if rng.random() > 0.49 else "SHORT"

                # Timestamps: exit_time must strictly be after entry_time
                exit_dt = ref_start_dt + timedelta(seconds=offsets[trade_idx])
                duration_minutes = max(2, int(rng.gauss(profile["avg_hold_minutes"], profile["avg_hold_minutes"] * 0.4)))
                entry_dt = exit_dt - timedelta(minutes=duration_minutes)

                entry_time_str = entry_dt.isoformat()
                exit_time_str = exit_dt.isoformat()

                # Sizing
                quantity = round(rng.uniform(profile["base_lot_min"], profile["base_lot_max"]), 2)

                # Entry Price variation
                price_volatility = 0.015 if asset_class in ("Forex", "Stock") else 0.04
                entry_price = round(base_price * (1.0 + rng.uniform(-price_volatility, price_volatility)), 5 if "JPY" not in symbol and asset_class == "Forex" else 2)

                # Outcome determination
                outcome_roll = rng.random()
                target_wr = profile["win_rate_target"]
                be_rate = profile["breakeven_rate"]

                rr_plan = round(rng.uniform(profile["rr_target_min"], profile["rr_target_max"]), 2)
                # Risk calculation (~0.8% - 1.5% of account balance)
                planned_risk = round(profile["starting_balance"] * rng.uniform(0.008, 0.018), 2)
                risk_pct = round((planned_risk / profile["starting_balance"]) * 100.0, 2)

                # Stop loss & Take profit levels based on realistic technical distance
                sl_dist_pct = rng.uniform(0.003, 0.015)
                sl_dist = entry_price * sl_dist_pct
                if "JPY" not in symbol and asset_class == "Forex":
                    sl_dist = max(0.0010, round(sl_dist, 5))
                else:
                    sl_dist = max(0.1, round(sl_dist, 2))

                if direction == "LONG":
                    sl_price = round(max(0.0001, entry_price - sl_dist), 5 if "JPY" not in symbol and asset_class == "Forex" else 2)
                    tp_price = round(entry_price + (sl_dist * rr_plan), 5 if "JPY" not in symbol and asset_class == "Forex" else 2)
                else:
                    sl_price = round(entry_price + sl_dist, 5 if "JPY" not in symbol and asset_class == "Forex" else 2)
                    tp_price = round(max(0.0001, entry_price - (sl_dist * rr_plan)), 5 if "JPY" not in symbol and asset_class == "Forex" else 2)

                if "JPY" in symbol:
                    planned_risk = round((sl_dist / entry_price) * quantity * contract_size, 2)
                else:
                    planned_risk = round(sl_dist * quantity * contract_size, 2)
                risk_pct = round((planned_risk / profile["starting_balance"]) * 100.0, 2)

                # Costs
                commission = round(quantity * rng.uniform(3.0, 6.0), 2)  # $3 - $6 per lot
                other_fees = round(quantity * rng.uniform(0.1, 0.5), 2)
                # Swap: overnight holding incurs small signed adjustment
                if duration_minutes > 1440:
                    signed_swap = round(rng.uniform(-4.5, 2.5) * (duration_minutes / 1440.0), 2)
                else:
                    signed_swap = 0.0

                # Determine exit price based on outcome
                outcome_roll = rng.random()
                target_wr = profile["win_rate_target"]
                be_rate = profile["breakeven_rate"]

                if outcome_roll < target_wr:
                    # Winning trade
                    mult = rng.uniform(0.85, 1.25) * rr_plan
                    exit_price = entry_price + (sl_dist * mult) if direction == "LONG" else entry_price - (sl_dist * mult)
                elif outcome_roll < (target_wr + be_rate):
                    # Breakeven trade
                    if "JPY" in symbol:
                        be_gross = commission + other_fees - signed_swap
                        denom = 1.0 - (be_gross / (quantity * contract_size)) if direction == "LONG" else 1.0 + (be_gross / (quantity * contract_size))
                        exit_price = entry_price / max(0.01, denom)
                    else:
                        be_gross = commission + other_fees - signed_swap
                        delta = be_gross / (quantity * contract_size)
                        exit_price = entry_price + delta if direction == "LONG" else entry_price - delta
                else:
                    # Losing trade
                    loss_mult = rng.uniform(0.7, 1.15)
                    exit_price = entry_price - (sl_dist * loss_mult) if direction == "LONG" else entry_price + (sl_dist * loss_mult)

                exit_price = round(max(0.0001, exit_price), 5 if "JPY" not in symbol and asset_class == "Forex" else 2)

                # Authoritative calculation pass to ensure 100% internal arithmetic consistency
                calc_res = compute_trade_pnl(
                    direction=direction,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=quantity,
                    symbol=symbol,
                    contract_size=contract_size,
                    commission=commission,
                    other_fees=other_fees,
                    signed_swap_adjustment=signed_swap,
                    planned_risk_amount=planned_risk,
                )

                strategy = rng.choice(profile["setups"])
                session = rng.choice(profile["sessions"])

                # Emotional state and notes
                if u_id == "demo_trader_07":  # Emotional trader
                    emotion = rng.choice(erratic_states if calc_res["net_pnl"] < 0 else emotional_states)
                    plan_followed = 0 if rng.random() > 0.4 else 1
                    notes = "Chased impulsive breakout without confirmation" if plan_followed == 0 else "Attempted setup."
                    mistakes = "Violated stop loss rules" if plan_followed == 0 else ""
                else:
                    emotion = rng.choice(emotional_states)
                    plan_followed = 1
                    notes = rng.choice(notes_templates)
                    mistakes = ""

                tags = f"{session},{asset_class},{direction}"

                trades_batch.append(
                    (
                        trade_id,
                        u_id,
                        symbol,
                        asset_class,
                        direction,
                        "CLOSED",
                        1,  # is_demo = True
                        entry_time_str,
                        exit_time_str,
                        entry_price,
                        exit_price,
                        quantity,
                        contract_size,
                        profile["currency"],
                        sl_price,
                        tp_price,
                        planned_risk,
                        risk_pct,
                        rr_plan,
                        calc_res["realized_r_multiple"],
                        calc_res["gross_pnl"],
                        calc_res["commission"],
                        calc_res["other_fees"],
                        calc_res["signed_swap_adjustment"],
                        calc_res["net_pnl"],
                        strategy,
                        session,
                        tags,
                        notes,
                        emotion,
                        plan_followed,
                        mistakes,
                        settings.DEMO_SEED_BATCH,
                        entry_time_str,
                        exit_time_str,
                    )
                )

            # Insert trader's batch of 10,000 trades in one fast transaction
            conn.executemany(trade_insert_sql, trades_batch)
            total_trades_generated += len(trades_batch)

    status_final = check_demo_dataset_status(db_path)
    return {
        "status": "SUCCESSFULLY_SEEDED",
        "demo_users_count": status_final["demo_users_count"],
        "demo_trades_count": status_final["demo_trades_count"],
        "closed_demo_trades_count": status_final["closed_demo_trades_count"],
        "trades_per_user": status_final["trades_per_user"],
        "seed_batch": settings.DEMO_SEED_BATCH,
        "is_healthy": status_final["is_complete"],
    }
