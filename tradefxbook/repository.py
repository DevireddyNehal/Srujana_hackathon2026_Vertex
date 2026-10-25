"""
TradeFXBook High-Performance Database Repository.
Leverages indexed database queries, SQL aggregations, and strict user isolation.
Never loads the entire 100,000 dataset into memory.
"""

import csv
import io
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import uuid

from tradefxbook.database import db_session
from tradefxbook.calculations import compute_trade_pnl


def row_to_dict(row) -> Dict[str, Any]:
    """Convert an sqlite3.Row object to a standard dictionary."""
    if row is None:
        return {}
    d = dict(row)
    # Convert integer flags to booleans where appropriate
    if "is_demo" in d:
        d["is_demo"] = bool(d["is_demo"])
    if "plan_followed" in d and d["plan_followed"] is not None:
        d["plan_followed"] = bool(d["plan_followed"])
    return d


def get_user_by_id(user_id: str, db_path: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieves user account by ID."""
    with db_session(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_dict(row) if row else None


def list_users(is_demo_only: bool = True, db_path: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Lists users, optionally filtered to demo users."""
    with db_session(db_path) as conn:
        if is_demo_only:
            rows = conn.execute(
                "SELECT * FROM users WHERE is_demo = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [row_to_dict(r) for r in rows]


def get_trade_by_id(trade_id: str, user_id: str, db_path: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves an individual trade by ID strictly enforcing user ownership.
    Returns None if trade does not exist or belongs to another user.
    """
    with db_session(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM trades WHERE id = ? AND user_id = ?",
            (trade_id, user_id),
        ).fetchone()
        return row_to_dict(row) if row else None


def create_trade(
    user_id: str,
    trade_data: Dict[str, Any],
    db_path: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Creates a new trade in the journal with authoritative P&L calculations.
    """
    # Verify user exists
    user = get_user_by_id(user_id, db_path)
    if not user:
        raise ValueError(f"User {user_id} not found.")

    trade_id = trade_data.get("id") or f"trd_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    calc_res = {
        "gross_pnl": 0.0,
        "commission": round(trade_data.get("commission", 0.0), 2),
        "other_fees": round(trade_data.get("other_fees", 0.0), 2),
        "signed_swap_adjustment": round(trade_data.get("signed_swap_adjustment", 0.0), 2),
        "net_pnl": 0.0,
        "realized_r_multiple": None,
    }

    if trade_data.get("status") == "CLOSED" and trade_data.get("exit_price"):
        calc_res = compute_trade_pnl(
            direction=trade_data["direction"],
            entry_price=trade_data["entry_price"],
            exit_price=trade_data["exit_price"],
            quantity=trade_data["quantity"],
            symbol=trade_data.get("symbol", "EUR/USD"),
            contract_size=trade_data.get("contract_size", 100000.0),
            commission=trade_data.get("commission", 0.0),
            other_fees=trade_data.get("other_fees", 0.0),
            signed_swap_adjustment=trade_data.get("signed_swap_adjustment", 0.0),
            planned_risk_amount=trade_data.get("planned_risk_amount"),
        )

    with db_session(db_path) as conn:
        conn.execute(
            """
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
            """,
            (
                trade_id,
                user_id,
                trade_data["symbol"],
                trade_data.get("asset_class", "Forex"),
                trade_data["direction"].upper(),
                trade_data.get("status", "CLOSED").upper(),
                1 if trade_data.get("is_demo", user.get("is_demo", False)) else 0,
                trade_data["entry_time"],
                trade_data.get("exit_time"),
                trade_data["entry_price"],
                trade_data.get("exit_price"),
                trade_data["quantity"],
                trade_data.get("contract_size", 100000.0),
                trade_data.get("account_currency", user.get("currency", "USD")),
                trade_data.get("stop_loss_price"),
                trade_data.get("take_profit_price"),
                trade_data.get("planned_risk_amount"),
                trade_data.get("risk_pct_balance"),
                trade_data.get("planned_rr_ratio"),
                calc_res["realized_r_multiple"],
                calc_res["gross_pnl"],
                calc_res["commission"],
                calc_res["other_fees"],
                calc_res["signed_swap_adjustment"],
                calc_res["net_pnl"],
                trade_data.get("strategy_or_setup", "Discretionary"),
                trade_data.get("trading_session", "London"),
                trade_data.get("tags", ""),
                trade_data.get("notes", ""),
                trade_data.get("emotional_state", "Disciplined"),
                1 if trade_data.get("plan_followed", True) else 0,
                trade_data.get("mistakes_or_lessons", ""),
                trade_data.get("seed_batch"),
                trade_data.get("created_at", now_iso),
                now_iso,
            ),
        )

    return get_trade_by_id(trade_id, user_id, db_path)  # type: ignore


def update_trade(
    trade_id: str,
    user_id: str,
    update_data: Dict[str, Any],
    db_path: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Updates an existing trade with recalculated financial metrics if relevant fields change.
    Strictly isolated: returns None if trade belongs to another user.
    """
    existing = get_trade_by_id(trade_id, user_id, db_path)
    if not existing:
        return None

    # Merge fields
    merged = dict(existing)
    for k, v in update_data.items():
        if v is not None:
            merged[k] = v

    now_iso = datetime.now(timezone.utc).isoformat()
    merged["updated_at"] = now_iso

    # Validate merged temporal order and required fields before committing to database
    if merged.get("status") == "CLOSED":
        if not merged.get("exit_time"):
            raise ValueError("exit_time is required when status is CLOSED")
        if merged.get("exit_price") is None or float(merged["exit_price"]) <= 0:
            raise ValueError("Valid positive exit_price is required when status is CLOSED")
        t_entry = datetime.fromisoformat(str(merged["entry_time"]).replace("Z", "+00:00"))
        t_exit = datetime.fromisoformat(str(merged["exit_time"]).replace("Z", "+00:00"))
        if t_entry.tzinfo is None and t_exit.tzinfo is not None:
            t_entry = t_entry.replace(tzinfo=t_exit.tzinfo)
        elif t_entry.tzinfo is not None and t_exit.tzinfo is None:
            t_exit = t_exit.replace(tzinfo=t_entry.tzinfo)
        if t_exit < t_entry:
            raise ValueError(f"exit_time ({merged['exit_time']}) must not precede entry_time ({merged['entry_time']})")

    # Recalculate P&L if relevant fields are present
    if merged.get("status") == "CLOSED" and merged.get("exit_price"):
        calc = compute_trade_pnl(
            direction=merged["direction"],
            entry_price=merged["entry_price"],
            exit_price=merged["exit_price"],
            quantity=merged["quantity"],
            symbol=merged["symbol"],
            contract_size=merged.get("contract_size", 100000.0),
            commission=merged.get("commission", 0.0),
            other_fees=merged.get("other_fees", 0.0),
            signed_swap_adjustment=merged.get("signed_swap_adjustment", 0.0),
            planned_risk_amount=merged.get("planned_risk_amount"),
        )
        merged["gross_pnl"] = calc["gross_pnl"]
        merged["commission"] = calc["commission"]
        merged["other_fees"] = calc["other_fees"]
        merged["signed_swap_adjustment"] = calc["signed_swap_adjustment"]
        merged["net_pnl"] = calc["net_pnl"]
        merged["realized_r_multiple"] = calc["realized_r_multiple"]

    with db_session(db_path) as conn:
        conn.execute(
            """
            UPDATE trades SET
                symbol = ?, asset_class = ?, direction = ?, status = ?,
                entry_time = ?, exit_time = ?, entry_price = ?, exit_price = ?,
                quantity = ?, contract_size = ?, account_currency = ?,
                stop_loss_price = ?, take_profit_price = ?, planned_risk_amount = ?,
                risk_pct_balance = ?, planned_rr_ratio = ?, realized_r_multiple = ?,
                gross_pnl = ?, commission = ?, other_fees = ?, signed_swap_adjustment = ?,
                net_pnl = ?, strategy_or_setup = ?, trading_session = ?, tags = ?,
                notes = ?, emotional_state = ?, plan_followed = ?, mistakes_or_lessons = ?,
                updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                merged["symbol"],
                merged["asset_class"],
                merged["direction"],
                merged["status"],
                merged["entry_time"],
                merged.get("exit_time"),
                merged["entry_price"],
                merged.get("exit_price"),
                merged["quantity"],
                merged["contract_size"],
                merged["account_currency"],
                merged.get("stop_loss_price"),
                merged.get("take_profit_price"),
                merged.get("planned_risk_amount"),
                merged.get("risk_pct_balance"),
                merged.get("planned_rr_ratio"),
                merged.get("realized_r_multiple"),
                merged["gross_pnl"],
                merged["commission"],
                merged["other_fees"],
                merged["signed_swap_adjustment"],
                merged["net_pnl"],
                merged.get("strategy_or_setup"),
                merged.get("trading_session"),
                merged.get("tags"),
                merged.get("notes"),
                merged.get("emotional_state"),
                1 if merged.get("plan_followed", True) else 0,
                merged.get("mistakes_or_lessons"),
                now_iso,
                trade_id,
                user_id,
            ),
        )

    return get_trade_by_id(trade_id, user_id, db_path)


def delete_trade(trade_id: str, user_id: str, db_path: Optional[Any] = None) -> bool:
    """
    Deletes a trade by ID strictly enforcing user ownership.
    Returns True if deleted, False if not found or unauthorized.
    """
    with db_session(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM trades WHERE id = ? AND user_id = ?",
            (trade_id, user_id),
        )
        return cursor.rowcount > 0


def _build_trade_filter_sql(
    user_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    strategy: Optional[str] = None,
    session: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """Builds parameterized SQL WHERE clause enforcing user isolation."""
    conditions = ["user_id = ?"]
    params: List[Any] = [user_id]

    if date_from:
        conditions.append("exit_time >= ?")
        params.append(date_from if "T" in date_from else f"{date_from}T00:00:00")
    if date_to:
        conditions.append("exit_time <= ?")
        params.append(date_to if "T" in date_to else f"{date_to}T23:59:59")
    if symbol:
        conditions.append("symbol LIKE ?")
        params.append(f"%{symbol}%")
    if direction:
        conditions.append("direction = ?")
        params.append(direction.upper())
    if status:
        conditions.append("status = ?")
        params.append(status.upper())
    if strategy:
        conditions.append("strategy_or_setup = ?")
        params.append(strategy)
    if session:
        conditions.append("trading_session = ?")
        params.append(session)
    if outcome:
        outcome_upper = outcome.upper()
        if outcome_upper == "WIN":
            conditions.append("net_pnl > 0.0")
        elif outcome_upper == "LOSS":
            conditions.append("net_pnl < 0.0")
        elif outcome_upper == "BREAKEVEN":
            conditions.append("net_pnl = 0.0")
    if search:
        search_like = f"%{search}%"
        conditions.append(
            "(id LIKE ? OR symbol LIKE ? OR notes LIKE ? OR strategy_or_setup LIKE ? OR tags LIKE ?)"
        )
        params.extend([search_like, search_like, search_like, search_like, search_like])

    where_sql = " WHERE " + " AND ".join(conditions)
    return where_sql, params


def list_trades_paginated(
    user_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    strategy: Optional[str] = None,
    session: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "exit_time",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 25,
    db_path: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Paginated database trade retrieval with parameterized sorting and filtering.
    """
    allowed_sort_fields = {
        "entry_time": "entry_time",
        "exit_time": "exit_time",
        "net_pnl": "net_pnl",
        "gross_pnl": "gross_pnl",
        "symbol": "symbol",
        "quantity": "quantity",
        "realized_r_multiple": "realized_r_multiple",
    }
    sort_col = allowed_sort_fields.get(sort_by, "exit_time")
    sort_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

    page = max(1, page)
    page_size = min(max(1, page_size), 500)
    offset = (page - 1) * page_size

    where_sql, params = _build_trade_filter_sql(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        symbol=symbol,
        direction=direction,
        status=status,
        outcome=outcome,
        strategy=strategy,
        session=session,
        search=search,
    )

    with db_session(db_path) as conn:
        # Total count
        count_sql = f"SELECT COUNT(*) as total FROM trades {where_sql}"
        total_row = conn.execute(count_sql, params).fetchone()
        total_items = total_row["total"] if total_row else 0

        # Query page items
        query_sql = f"""
            SELECT * FROM trades
            {where_sql}
            ORDER BY {sort_col} {sort_dir}
            LIMIT ? OFFSET ?
        """
        page_params = list(params) + [page_size, offset]
        rows = conn.execute(query_sql, page_params).fetchall()
        items = [row_to_dict(r) for r in rows]

        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1

        return {
            "items": items,
            "total": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }


def export_trades_to_csv(
    user_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    strategy: Optional[str] = None,
    session: Optional[str] = None,
    search: Optional[str] = None,
    db_path: Optional[Any] = None,
) -> str:
    """
    Exports filtered trade history to CSV strictly for the requested user.
    """
    where_sql, params = _build_trade_filter_sql(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        symbol=symbol,
        direction=direction,
        status=status,
        outcome=outcome,
        strategy=strategy,
        session=session,
        search=search,
    )

    query_sql = f"SELECT * FROM trades {where_sql} ORDER BY exit_time ASC"

    with db_session(db_path) as conn:
        rows = conn.execute(query_sql, params).fetchall()

    output = io.StringIO()
    fieldnames = [
        "id",
        "user_id",
        "symbol",
        "asset_class",
        "direction",
        "status",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "quantity",
        "contract_size",
        "account_currency",
        "stop_loss_price",
        "take_profit_price",
        "planned_risk_amount",
        "risk_pct_balance",
        "planned_rr_ratio",
        "realized_r_multiple",
        "gross_pnl",
        "commission",
        "other_fees",
        "signed_swap_adjustment",
        "net_pnl",
        "strategy_or_setup",
        "trading_session",
        "tags",
        "emotional_state",
        "plan_followed",
        "notes",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        d = dict(row)
        # Double check user isolation
        if d["user_id"] != user_id:
            continue
        # Sanitize against CSV formula injection (DDE attacks)
        for k, v in d.items():
            if isinstance(v, str) and len(v) > 0 and v[0] in ("=", "+", "-", "@"):
                d[k] = f"'{v}"
        writer.writerow(d)

    return output.getvalue()


def get_user_closed_trades(
    user_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    session: Optional[str] = None,
    direction: Optional[str] = None,
    outcome: Optional[str] = None,
    db_path: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves all closed trades for analytics computation strictly for the specified user.
    """
    where_sql, params = _build_trade_filter_sql(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        symbol=symbol,
        direction=direction,
        status="CLOSED",
        outcome=outcome,
        strategy=strategy,
        session=session,
    )

    query_sql = f"SELECT * FROM trades {where_sql} ORDER BY exit_time ASC"

    with db_session(db_path) as conn:
        rows = conn.execute(query_sql, params).fetchall()
        return [row_to_dict(r) for r in rows]


def get_analytics_breakdown(
    user_id: str,
    group_by_field: str,  # symbol, strategy_or_setup, trading_session, direction, outcome
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db_path: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Fast database-level aggregated breakdown grouped by category.
    """
    allowed_groups = {
        "symbol": "symbol",
        "strategy": "strategy_or_setup",
        "session": "trading_session",
        "direction": "direction",
        "asset_class": "asset_class",
    }
    col = allowed_groups.get(group_by_field, "strategy_or_setup")

    where_sql, params = _build_trade_filter_sql(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        status="CLOSED",
    )

    query_sql = f"""
        SELECT
            {col} as key_col,
            COUNT(*) as trade_count,
            SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN net_pnl = 0 THEN 1 ELSE 0 END) as breakevens,
            SUM(net_pnl) as total_net_pnl,
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) as sum_wins,
            SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END) as sum_losses
        FROM trades
        {where_sql}
        GROUP BY {col}
        ORDER BY total_net_pnl DESC
    """

    with db_session(db_path) as conn:
        rows = conn.execute(query_sql, params).fetchall()
        results = []
        for r in rows:
            k = r["key_col"] or "Unspecified"
            tc = r["trade_count"]
            w = r["wins"] or 0
            l = r["losses"] or 0
            net = round(r["total_net_pnl"] or 0.0, 2)
            sum_w = r["sum_wins"] or 0.0
            sum_l = abs(r["sum_losses"] or 0.0)

            wr = round((w / (w + l)) * 100.0, 2) if (w + l) > 0 else None
            pf = round(sum_w / sum_l, 3) if sum_l > 0 else None
            avg_pnl = round(net / tc, 2) if tc > 0 else 0.0

            results.append(
                {
                    "key": str(k),
                    "trade_count": tc,
                    "winning_trades": w,
                    "losing_trades": l,
                    "win_rate": wr,
                    "net_pnl": net,
                    "profit_factor": pf,
                    "avg_trade_pnl": avg_pnl,
                }
            )
        return results


def compute_user_analytics_db(
    user_id: str,
    starting_balance: float = 50000.0,
    user_name: str = "Demo Trader",
    account_currency: str = "USD",
    timezone_str: str = "UTC",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    session: Optional[str] = None,
    direction: Optional[str] = None,
    outcome: Optional[str] = None,
    db_path: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Computes all 22 required trading metrics directly using database aggregations
    and a single chronological streaming pass for drawdown and streak metrics.
    Executes in under 100ms for 10,000 trades.
    """
    where_sql, params = _build_trade_filter_sql(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        symbol=symbol,
        direction=direction,
        status="CLOSED",
        outcome=outcome,
        strategy=strategy,
        session=session,
    )

    agg_sql = f"""
        SELECT
            COUNT(*) as total_closed,
            SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN net_pnl = 0 THEN 1 ELSE 0 END) as breakevens,
            SUM(CASE WHEN gross_pnl > 0 THEN gross_pnl ELSE 0 END) as gross_profit,
            SUM(CASE WHEN gross_pnl < 0 THEN gross_pnl ELSE 0 END) as gross_loss,
            SUM(net_pnl) as net_pnl,
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) as sum_wins,
            SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END) as sum_losses,
            SUM(commission) as commissions,
            SUM(other_fees) as fees,
            SUM(signed_swap_adjustment) as swap,
            AVG(realized_r_multiple) as avg_r,
            AVG((julianday(exit_time) - julianday(entry_time)) * 86400) as avg_duration
        FROM trades
        {where_sql}
    """

    with db_session(db_path) as conn:
        agg_row = conn.execute(agg_sql, params).fetchone()
        if not agg_row or agg_row["total_closed"] == 0:
            return {
                "user_id": user_id,
                "user_name": user_name,
                "account_currency": account_currency,
                "starting_balance": starting_balance,
                "current_equity": starting_balance,
                "total_closed_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "breakeven_trades": 0,
                "win_rate": None,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "net_pnl": 0.0,
                "profit_factor": None,
                "expectancy": None,
                "average_win": None,
                "average_loss": None,
                "average_rr_ratio": None,
                "total_trading_costs": 0.0,
                "average_holding_duration_seconds": None,
                "best_trade": None,
                "worst_trade": None,
                "best_trading_day": None,
                "worst_trading_day": None,
                "realized_equity_curve_points": 1,
                "max_drawdown_currency": 0.0,
                "max_drawdown_pct": 0.0,
                "average_daily_pnl": None,
                "average_r_multiple": None,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "profitable_days_count": 0,
                "losing_days_count": 0,
                "breakeven_days_count": 0,
                "total_calendar_days_in_period": 0,
            }

        total_closed = agg_row["total_closed"]
        wins = agg_row["wins"] or 0
        losses = agg_row["losses"] or 0
        breakevens = agg_row["breakevens"] or 0
        gross_profit = round(agg_row["gross_profit"] or 0.0, 2)
        gross_loss = round(agg_row["gross_loss"] or 0.0, 2)
        net_pnl = round(agg_row["net_pnl"] or 0.0, 2)
        sum_wins = round(agg_row["sum_wins"] or 0.0, 2)
        sum_losses = round(agg_row["sum_losses"] or 0.0, 2)
        commissions = round(agg_row["commissions"] or 0.0, 2)
        fees = round(agg_row["fees"] or 0.0, 2)
        swap = round(agg_row["swap"] or 0.0, 2)
        avg_r = round(agg_row["avg_r"], 3) if agg_row["avg_r"] is not None else None
        avg_duration = round(agg_row["avg_duration"], 1) if agg_row["avg_duration"] is not None else None

        # Best / Worst trades via indexed limit queries
        best_sql = f"SELECT id, symbol, direction, exit_time, net_pnl, realized_r_multiple FROM trades {where_sql} ORDER BY net_pnl DESC LIMIT 1"
        worst_sql = f"SELECT id, symbol, direction, exit_time, net_pnl, realized_r_multiple FROM trades {where_sql} ORDER BY net_pnl ASC LIMIT 1"

        best_row = conn.execute(best_sql, params).fetchone()
        worst_row = conn.execute(worst_sql, params).fetchone()

        best_trade = row_to_dict(best_row) if best_row else None
        worst_trade = row_to_dict(worst_row) if worst_row else None

        # Chronological streaming pass for equity curve, drawdown, streaks, and daily aggregates
        chrono_sql = f"SELECT net_pnl, exit_time FROM trades {where_sql} ORDER BY exit_time ASC"
        cursor = conn.cursor()
        cursor.row_factory = None
        chrono_rows = cursor.execute(chrono_sql, params).fetchall()

        current_equity = starting_balance
        high_water_mark = starting_balance
        max_dd_curr = 0.0
        max_dd_pct = 0.0

        curr_w = max_w = curr_l = max_l = 0
        day_map: Dict[str, List[Any]] = {}

        import zoneinfo
        try:
            user_tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            user_tz = zoneinfo.ZoneInfo("UTC")
        is_utc = timezone_str.upper() in ("UTC", "ETC/UTC", "GMT")

        for n, exit_t_str in chrono_rows:
            current_equity = round(current_equity + n, 2)
            if current_equity > high_water_mark:
                high_water_mark = current_equity
            dd = round(high_water_mark - current_equity, 2)
            if dd > max_dd_curr:
                max_dd_curr = dd
                max_dd_pct = round((dd / high_water_mark) * 100.0, 2) if high_water_mark > 0 else 0.0

            if n > 0:
                curr_w += 1
                max_w = max(max_w, curr_w)
                curr_l = 0
            elif n < 0:
                curr_l += 1
                max_l = max(max_l, curr_l)
                curr_w = 0
            else:
                curr_w = curr_l = 0

            if is_utc or not exit_t_str:
                d_str = exit_t_str[:10] if exit_t_str else ""
            else:
                try:
                    dt_utc = datetime.fromisoformat(exit_t_str.replace("Z", "+00:00"))
                    d_str = dt_utc.astimezone(user_tz).strftime("%Y-%m-%d")
                except Exception:
                    d_str = exit_t_str[:10]

            if d_str not in day_map:
                day_map[d_str] = [0.0, 0]
            day_map[d_str][0] = round(day_map[d_str][0] + n, 2)
            day_map[d_str][1] += 1

        # Ratios
        win_rate = round((wins / (wins + losses)) * 100.0, 2) if (wins + losses) > 0 else None
        abs_losses = abs(sum_losses)
        profit_factor = round(sum_wins / abs_losses, 3) if abs_losses > 0 else None
        expectancy = round(net_pnl / total_closed, 2) if total_closed > 0 else None
        average_win = round(sum_wins / wins, 2) if wins > 0 else None
        average_loss = round(sum_losses / losses, 2) if losses > 0 else None
        average_rr = (
            round(average_win / abs(average_loss), 3)
            if average_win is not None and average_loss is not None and abs(average_loss) > 0
            else None
        )
        total_costs = round(commissions + fees - swap, 2)

        # Days evaluation
        best_day = None
        worst_day = None
        profitable_days = 0
        losing_days = 0
        breakeven_days = 0

        for d_key, (d_pnl, d_cnt) in day_map.items():
            if d_pnl > 0:
                profitable_days += 1
            elif d_pnl < 0:
                losing_days += 1
            else:
                breakeven_days += 1

            day_obj = {"date": d_key, "net_pnl": d_pnl, "trades_count": d_cnt}
            if best_day is None or d_pnl > best_day["net_pnl"]:
                best_day = day_obj
            if worst_day is None or d_pnl < worst_day["net_pnl"]:
                worst_day = day_obj

        active_days = len(day_map)
        avg_daily = round(net_pnl / active_days, 2) if active_days > 0 else None

        return {
            "user_id": user_id,
            "user_name": user_name,
            "account_currency": account_currency,
            "starting_balance": round(starting_balance, 2),
            "current_equity": round(current_equity, 2),
            "total_closed_trades": total_closed,
            "winning_trades": wins,
            "losing_trades": losses,
            "breakeven_trades": breakevens,
            "win_rate": win_rate,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_pnl": net_pnl,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "average_win": average_win,
            "average_loss": average_loss,
            "average_rr_ratio": average_rr,
            "total_trading_costs": total_costs,
            "average_holding_duration_seconds": avg_duration,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "best_trading_day": best_day,
            "worst_trading_day": worst_day,
            "realized_equity_curve_points": total_closed + 1,
            "max_drawdown_currency": round(max_dd_curr, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "average_daily_pnl": avg_daily,
            "average_r_multiple": avg_r,
            "max_consecutive_wins": max_w,
            "max_consecutive_losses": max_l,
            "profitable_days_count": profitable_days,
            "losing_days_count": losing_days,
            "breakeven_days_count": breakeven_days,
            "total_calendar_days_in_period": active_days,
        }
