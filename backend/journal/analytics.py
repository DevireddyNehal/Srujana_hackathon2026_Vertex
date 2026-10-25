from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Any


def _period_key(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%Y-%m")


def analyze_trades(trades: list[dict[str, Any]]) -> dict[str, Any]:
    closed = [trade for trade in trades if trade.get("closed_at") is not None]
    ordered = sorted(closed, key=lambda trade: (trade["closed_at"], trade["id"]))
    pnls = [float(trade["net_pnl"]) for trade in ordered]
    winners = [pnl for pnl in pnls if pnl > 0]
    losers = [pnl for pnl in pnls if pnl < 0]
    gross_profit = sum(winners)
    gross_loss = -sum(losers)
    expectancy = sum(pnls) / len(pnls) if pnls else 0

    equity = peak = max_drawdown = 0.0
    curve: list[dict[str, float | str]] = []
    monthly: dict[str, float] = defaultdict(float)
    symbols: dict[str, dict[str, float | int]] = defaultdict(lambda: {"trades": 0, "net_pnl": 0.0})
    strategies: dict[str, dict[str, float | int]] = defaultdict(lambda: {"trades": 0, "net_pnl": 0.0})
    r_values: list[float] = []
    for trade, pnl in zip(ordered, pnls, strict=True):
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        curve.append({"date": trade["closed_at"], "equity": round(equity, 2)})
        monthly[_period_key(trade["closed_at"])] += pnl
        symbols[trade["symbol"]]["trades"] += 1
        symbols[trade["symbol"]]["net_pnl"] += pnl
        strategy = trade.get("strategy") or "Unspecified"
        strategies[strategy]["trades"] += 1
        strategies[strategy]["net_pnl"] += pnl
        if trade.get("r_multiple") is not None:
            r_values.append(float(trade["r_multiple"]))

    return {
        "summary": {
            "trade_count": len(ordered),
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate_pct": round(len(winners) / len(ordered) * 100, 2) if ordered else 0.0,
            "net_pnl": round(sum(pnls), 2),
            "average_win": round(sum(winners) / len(winners), 2) if winners else 0.0,
            "average_loss": round(sum(losers) / len(losers), 2) if losers else 0.0,
            "expectancy": round(expectancy, 2),
            "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else None,
            "max_drawdown": round(max_drawdown, 2),
            "average_r_multiple": round(sum(r_values) / len(r_values), 4) if r_values else None,
        },
        "equity_curve": curve,
        "monthly_pnl": [
            {"month": month, "net_pnl": round(value, 2)}
            for month, value in sorted(monthly.items())
        ],
        "by_symbol": [
            {"symbol": symbol, "trades": int(value["trades"]), "net_pnl": round(float(value["net_pnl"]), 2)}
            for symbol, value in sorted(symbols.items(), key=lambda item: float(item[1]["net_pnl"]), reverse=True)
        ],
        "by_strategy": [
            {"strategy": strategy, "trades": int(value["trades"]), "net_pnl": round(float(value["net_pnl"]), 2)}
            for strategy, value in sorted(strategies.items(), key=lambda item: float(item[1]["net_pnl"]), reverse=True)
        ],
        "disclaimer": "Historical trading performance is descriptive and does not predict future results.",
    }
