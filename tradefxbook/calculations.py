"""
TradeFXBook Authoritative Trade and Analytical Calculation Service.
Ensures zero calculation discrepancies across the backend, dashboard, and tests.
Uses decimal-safe precision conventions for financial values.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import zoneinfo


def compute_trade_pnl(
    direction: str,
    entry_price: float,
    exit_price: float,
    quantity: float,
    symbol: str = "EUR/USD",
    contract_size: float = 100000.0,
    commission: float = 0.0,
    other_fees: float = 0.0,
    signed_swap_adjustment: float = 0.0,
    planned_risk_amount: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Authoritative realized trade performance calculation.
    Supports standard Forex pairs, quote-currency conversion pairs (e.g., USD/JPY),
    and non-forex asset classes.

    Formula:
        net_pnl = gross_pnl - commission - other_fees + signed_swap_adjustment
    """
    if entry_price <= 0 or exit_price <= 0 or quantity <= 0:
        raise ValueError("Prices and quantity must be strictly positive.")

    direction_upper = direction.upper()
    if direction_upper not in ("LONG", "SHORT"):
        raise ValueError(f"Invalid direction: {direction}. Must be LONG or SHORT.")

    sym_clean = symbol.upper().replace("/", "").replace("_", "")

    # Handle USD/JPY and similar inverse quote pairs where quote currency is JPY
    if sym_clean.startswith("USDJPY"):
        # Pip/point value is in JPY, converted back to USD by dividing by exit price
        if direction_upper == "LONG":
            gross_pnl = ((exit_price - entry_price) / exit_price) * quantity * contract_size
        else:
            gross_pnl = ((entry_price - exit_price) / exit_price) * quantity * contract_size
    else:
        # Standard pairs (EURUSD, GBPUSD, AUDUSD, XAUUSD, BTCUSD, US30, etc.)
        if direction_upper == "LONG":
            gross_pnl = (exit_price - entry_price) * quantity * contract_size
        else:
            gross_pnl = (entry_price - exit_price) * quantity * contract_size

    # Ensure precision is preserved to cents
    gross_pnl = round(gross_pnl, 2)
    comm = round(max(0.0, commission), 2)
    fees = round(max(0.0, other_fees), 2)
    swap = round(signed_swap_adjustment, 2)

    # Net P&L: fees and commissions subtract, positive swap adds, negative swap subtracts
    net_pnl = round(gross_pnl - comm - fees + swap, 2)

    # Realized R-Multiple
    realized_r_multiple: Optional[float] = None
    if planned_risk_amount is not None and planned_risk_amount > 0:
        realized_r_multiple = round(net_pnl / planned_risk_amount, 3)

    return {
        "gross_pnl": gross_pnl,
        "commission": comm,
        "other_fees": fees,
        "signed_swap_adjustment": swap,
        "net_pnl": net_pnl,
        "realized_r_multiple": realized_r_multiple,
    }


def compute_aggregate_metrics(
    trades: List[Dict[str, Any]],
    starting_balance: float = 50000.0,
    user_id: str = "demo_trader_01",
    user_name: str = "Demo Trader 01",
    account_currency: str = "USD",
    timezone_str: str = "UTC",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes all 22 required trading performance metrics + secondary statistics
    strictly from closed trade records.
    """
    closed_trades = [t for t in trades if t.get("status") == "CLOSED" and t.get("exit_time")]

    # Sort chronologically by exit_time for equity curve and streak calculations
    closed_trades.sort(key=lambda t: t["exit_time"])

    total_closed = len(closed_trades)
    if total_closed == 0:
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

    wins = 0
    losses = 0
    breakevens = 0

    gross_profit = 0.0
    gross_loss = 0.0
    total_net_pnl = 0.0

    pos_net_pnl_sum = 0.0
    neg_net_pnl_sum = 0.0

    total_commission = 0.0
    total_fees = 0.0
    total_swap = 0.0

    total_duration_sec = 0.0
    valid_duration_count = 0

    best_trade_item: Optional[Dict[str, Any]] = None
    worst_trade_item: Optional[Dict[str, Any]] = None

    r_multiples: List[float] = []

    # Consecutive streak tracking
    current_win_streak = 0
    max_win_streak = 0
    current_loss_streak = 0
    max_loss_streak = 0

    # Equity curve and drawdown tracking
    current_equity = starting_balance
    high_water_mark = starting_balance
    max_dd_curr = 0.0
    max_dd_pct = 0.0

    # Daily grouping in user timezone
    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")

    daily_pnl_map: Dict[str, Dict[str, Any]] = {}

    for t in closed_trades:
        net = round(float(t.get("net_pnl", 0.0)), 2)
        gross = round(float(t.get("gross_pnl", 0.0)), 2)
        comm = round(float(t.get("commission", 0.0)), 2)
        fee = round(float(t.get("other_fees", 0.0)), 2)
        swap = round(float(t.get("signed_swap_adjustment", 0.0)), 2)

        total_net_pnl += net
        total_commission += comm
        total_fees += fee
        total_swap += swap

        # Categorize win / loss / breakeven (tolerance: |net| < 0.005)
        if round(net, 2) > 0.00:
            wins += 1
            pos_net_pnl_sum += net
            current_win_streak += 1
            max_win_streak = max(max_win_streak, current_win_streak)
            current_loss_streak = 0
        elif round(net, 2) < 0.00:
            losses += 1
            neg_net_pnl_sum += net  # negative value
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
            current_win_streak = 0
        else:
            breakevens += 1
            current_win_streak = 0
            current_loss_streak = 0

        if gross > 0:
            gross_profit += gross
        else:
            gross_loss += gross  # negative

        # Holding duration
        entry_t_str = t.get("entry_time")
        exit_t_str = t.get("exit_time")
        if entry_t_str and exit_t_str:
            try:
                t_in = datetime.fromisoformat(entry_t_str.replace("Z", "+00:00"))
                t_out = datetime.fromisoformat(exit_t_str.replace("Z", "+00:00"))
                duration = (t_out - t_in).total_seconds()
                if duration >= 0:
                    total_duration_sec += duration
                    valid_duration_count += 1
            except Exception:
                pass

        # R-Multiple
        if t.get("realized_r_multiple") is not None:
            r_multiples.append(float(t["realized_r_multiple"]))

        # Best / Worst trade
        t_id = t.get("id", "mock_id")
        t_sym = t.get("symbol", "EUR/USD")
        t_dir = t.get("direction", "LONG")
        t_exit = t.get("exit_time", "")

        if best_trade_item is None or net > best_trade_item["net_pnl"]:
            best_trade_item = {
                "id": t_id,
                "symbol": t_sym,
                "direction": t_dir,
                "exit_time": t_exit,
                "net_pnl": net,
                "r_multiple": t.get("realized_r_multiple"),
            }
        if worst_trade_item is None or net < worst_trade_item["net_pnl"]:
            worst_trade_item = {
                "id": t_id,
                "symbol": t_sym,
                "direction": t_dir,
                "exit_time": t_exit,
                "net_pnl": net,
                "r_multiple": t.get("realized_r_multiple"),
            }

        # Equity progression & peak-to-trough Drawdown
        current_equity = round(current_equity + net, 2)
        if current_equity > high_water_mark:
            high_water_mark = current_equity

        dd_curr = round(high_water_mark - current_equity, 2)
        dd_pct = round((dd_curr / high_water_mark) * 100.0, 2) if high_water_mark > 0 else 0.0

        if dd_curr > max_dd_curr:
            max_dd_curr = dd_curr
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

        # Daily aggregation in user timezone
        try:
            dt_utc = datetime.fromisoformat(exit_t_str.replace("Z", "+00:00"))
            dt_local = dt_utc.astimezone(tz)
            date_key = dt_local.strftime("%Y-%m-%d")
        except Exception:
            date_key = exit_t_str[:10]

        if date_key not in daily_pnl_map:
            daily_pnl_map[date_key] = {"net_pnl": 0.0, "trades_count": 0}
        daily_pnl_map[date_key]["net_pnl"] = round(daily_pnl_map[date_key]["net_pnl"] + net, 2)
        daily_pnl_map[date_key]["trades_count"] += 1

    # Win rate: strictly wins / (wins + losses) * 100 (excluding breakeven)
    win_rate: Optional[float] = None
    if (wins + losses) > 0:
        win_rate = round((wins / (wins + losses)) * 100.0, 2)

    # Profit factor: sum(positive net P&L) / abs(sum(negative net P&L))
    profit_factor: Optional[float] = None
    abs_neg_sum = abs(neg_net_pnl_sum)
    if abs_neg_sum > 0:
        profit_factor = round(pos_net_pnl_sum / abs_neg_sum, 3)
    elif pos_net_pnl_sum > 0:
        profit_factor = None  # Undefined/infinite case: safely handled as None

    # Expectancy: sum(net_pnl) / total_closed_trades
    expectancy = round(total_net_pnl / total_closed, 2) if total_closed > 0 else None

    # Average Win / Average Loss
    average_win = round(pos_net_pnl_sum / wins, 2) if wins > 0 else None
    average_loss = round(neg_net_pnl_sum / losses, 2) if losses > 0 else None

    # Average Reward-to-Risk ratio: average_win / abs(average_loss)
    average_rr: Optional[float] = None
    if average_win is not None and average_loss is not None and abs(average_loss) > 0:
        average_rr = round(average_win / abs(average_loss), 3)

    # Total trading costs = commissions + other_fees - signed_swap
    total_trading_costs = round(total_commission + total_fees - total_swap, 2)

    # Average holding duration
    avg_duration_sec = (
        round(total_duration_sec / valid_duration_count, 1) if valid_duration_count > 0 else None
    )

    # Best & Worst trading days
    best_trading_day: Optional[Dict[str, Any]] = None
    worst_trading_day: Optional[Dict[str, Any]] = None
    profitable_days_count = 0
    losing_days_count = 0
    breakeven_days_count = 0

    for d_key, d_val in daily_pnl_map.items():
        d_pnl = d_val["net_pnl"]
        if d_pnl > 0:
            profitable_days_count += 1
        elif d_pnl < 0:
            losing_days_count += 1
        else:
            breakeven_days_count += 1

        day_obj = {"date": d_key, "net_pnl": d_pnl, "trades_count": d_val["trades_count"]}
        if best_trading_day is None or d_pnl > best_trading_day["net_pnl"]:
            best_trading_day = day_obj
        if worst_trading_day is None or d_pnl < worst_trading_day["net_pnl"]:
            worst_trading_day = day_obj

    # Average daily P&L across trading days
    active_days_count = len(daily_pnl_map)
    avg_daily_pnl = round(total_net_pnl / active_days_count, 2) if active_days_count > 0 else None

    # Average R-Multiple
    avg_r_mult = round(sum(r_multiples) / len(r_multiples), 3) if r_multiples else None

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
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "net_pnl": round(total_net_pnl, 2),
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "average_win": average_win,
        "average_loss": average_loss,
        "average_rr_ratio": average_rr,
        "total_trading_costs": total_trading_costs,
        "average_holding_duration_seconds": avg_duration_sec,
        "best_trade": best_trade_item,
        "worst_trade": worst_trade_item,
        "best_trading_day": best_trading_day,
        "worst_trading_day": worst_trading_day,
        "realized_equity_curve_points": total_closed + 1,
        "max_drawdown_currency": round(max_dd_curr, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "average_daily_pnl": avg_daily_pnl,
        "average_r_multiple": avg_r_mult,
        "max_consecutive_wins": max_win_streak,
        "max_consecutive_losses": max_loss_streak,
        "profitable_days_count": profitable_days_count,
        "losing_days_count": losing_days_count,
        "breakeven_days_count": breakeven_days_count,
        "total_calendar_days_in_period": len(daily_pnl_map),
    }


def generate_daily_pnl_series(
    trades: List[Dict[str, Any]],
    start_date: str,  # YYYY-MM-DD
    end_date: str,    # YYYY-MM-DD
    timezone_str: str = "UTC",
) -> List[Dict[str, Any]]:
    """
    Generates a continuous daily P&L time series for every calendar day in [start_date, end_date].
    Rules:
    1. Include only closed trades.
    2. Assign P&L to exit date converted to user timezone.
    3. Return 0 for days with no closed trades (including weekends & holidays).
    4. Sorted chronologically.
    5. Reconciles with closed trades total net P&L.
    """
    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")

    d_start = date.fromisoformat(start_date)
    d_end = date.fromisoformat(end_date)
    if d_end < d_start:
        d_start, d_end = d_end, d_start

    # Aggregate closed trades by user's calendar exit date
    daily_aggregates: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        if t.get("status") != "CLOSED" or not t.get("exit_time"):
            continue

        exit_t_str = t["exit_time"]
        try:
            dt_utc = datetime.fromisoformat(exit_t_str.replace("Z", "+00:00"))
            dt_local = dt_utc.astimezone(tz)
            day_str = dt_local.strftime("%Y-%m-%d")
        except Exception:
            day_str = exit_t_str[:10]

        # Only include if within calendar range
        if start_date <= day_str <= end_date:
            if day_str not in daily_aggregates:
                daily_aggregates[day_str] = {
                    "closed_trades_count": 0,
                    "gross_pnl": 0.0,
                    "commissions": 0.0,
                    "swap": 0.0,
                    "net_pnl": 0.0,
                }
            net = round(float(t.get("net_pnl", 0.0)), 2)
            gross = round(float(t.get("gross_pnl", 0.0)), 2)
            comm = round(float(t.get("commission", 0.0)), 2)
            swap = round(float(t.get("signed_swap_adjustment", 0.0)), 2)

            agg = daily_aggregates[day_str]
            agg["closed_trades_count"] += 1
            agg["gross_pnl"] = round(agg["gross_pnl"] + gross, 2)
            agg["commissions"] = round(agg["commissions"] + comm, 2)
            agg["swap"] = round(agg["swap"] + swap, 2)
            agg["net_pnl"] = round(agg["net_pnl"] + net, 2)

    # Build continuous chronological list for every day
    results: List[Dict[str, Any]] = []
    curr = d_start
    running_cumulative_pnl = 0.0

    while curr <= d_end:
        day_str = curr.strftime("%Y-%m-%d")
        agg = daily_aggregates.get(
            day_str,
            {
                "closed_trades_count": 0,
                "gross_pnl": 0.0,
                "commissions": 0.0,
                "swap": 0.0,
                "net_pnl": 0.0,
            },
        )
        running_cumulative_pnl = round(running_cumulative_pnl + agg["net_pnl"], 2)

        results.append(
            {
                "date": day_str,
                "closed_trades_count": agg["closed_trades_count"],
                "gross_pnl": agg["gross_pnl"],
                "commissions": agg["commissions"],
                "swap": agg["swap"],
                "net_pnl": agg["net_pnl"],
                "cumulative_net_pnl": running_cumulative_pnl,
                "is_winning_day": agg["net_pnl"] > 0,
                "is_breakeven_day": agg["net_pnl"] == 0,
            }
        )
        curr += timedelta(days=1)

    return results
