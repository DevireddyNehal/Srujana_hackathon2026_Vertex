from __future__ import annotations

from typing import Any


def trade_metrics(trade: dict[str, Any]) -> dict[str, float | None]:
    exit_price = trade.get("exit_price")
    if exit_price is None:
        return {"gross_pnl": None, "net_pnl": None, "return_pct": None, "r_multiple": None}

    direction = 1.0 if trade["side"] == "long" else -1.0
    entry_price = float(trade["entry_price"])
    quantity = float(trade["quantity"])
    gross_pnl = direction * (float(exit_price) - entry_price) * quantity
    net_pnl = gross_pnl - float(trade.get("fees", 0))
    return_pct = direction * (float(exit_price) - entry_price) / entry_price * 100
    stop_loss = trade.get("stop_loss")
    risk = abs(entry_price - float(stop_loss)) * quantity if stop_loss is not None else 0
    return {
        "gross_pnl": round(gross_pnl, 2),
        "net_pnl": round(net_pnl, 2),
        "return_pct": round(return_pct, 4),
        "r_multiple": round(net_pnl / risk, 4) if risk > 0 else None,
    }
