from __future__ import annotations

from typing import Any


def review_trade(trade: dict[str, Any]) -> dict[str, Any]:
    """Return a local, deterministic checklist review without external AI calls."""
    observations: list[str] = []
    suggestions: list[str] = []

    if trade.get("stop_loss") is None:
        observations.append("No stop-loss was recorded, so planned risk cannot be measured.")
        suggestions.append("Record an invalidation level before entering the next comparable setup.")
    elif trade.get("r_multiple") is not None:
        r_multiple = float(trade["r_multiple"])
        if r_multiple < 0:
            observations.append(f"The trade closed at {r_multiple:.2f}R after fees.")
            suggestions.append("Compare the exit with the original invalidation level and written plan.")
        elif r_multiple >= 2:
            observations.append(f"The trade returned {r_multiple:.2f}R after fees.")
            suggestions.append("Review which entry and management decisions were repeatable.")

    if not trade.get("strategy"):
        observations.append("No strategy was assigned.")
        suggestions.append("Tag the setup consistently to make later strategy comparisons useful.")
    if not trade.get("notes"):
        suggestions.append("Add a short note about the thesis and whether execution followed the plan.")

    if not observations:
        observations.append("The trade record includes a strategy and planned risk context.")
    if not suggestions:
        suggestions.append("Compare this trade with other trades using the same setup and market conditions.")

    return {
        "provider": "local-rules",
        "observations": observations,
        "suggestions": suggestions,
        "disclaimer": "This is a checklist generated from recorded fields, not personalized financial advice.",
    }
