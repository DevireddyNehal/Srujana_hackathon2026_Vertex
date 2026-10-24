"""
AI Scenario Translator, Conflict Detector, and Financial Guardrails Engine
Module: backend.engine.ai_agent
Role: Lead Sandbox (Natural Language to Shocks, Financial Trilemma Resolver, Assumptions, Tradeoffs)
"""

import math
import re
from typing import Any, Dict, List


def parse_custom_scenario(custom_prompt: str) -> Dict[str, Any]:
    """
    Translates free-form textual queries into parametric quantitative shocks.
    Bounds values within realistic financial guardrails to prevent erroneous spikes.
    """
    prompt_lower = (custom_prompt or "").lower()

    market_decline = 0.0
    rate_change_bps = 0
    currency_shift = 0.0
    sector_shocks: Dict[str, float] = {}
    preset_name = "Custom AI Scenario"

    # 1. Broad Market Crash / Decline Detection
    if any(k in prompt_lower for k in ["crash", "recession", "bear market", "meltdown"]):
        market_decline = -20.0
        preset_name = "Severe Market Downturn"
    elif any(k in prompt_lower for k in ["drop", "fall", "decline", "correction", "pullback"]):
        pct_match = re.search(r"(\d+(\.\d+)?)\s*%", prompt_lower)
        if pct_match:
            market_decline = -min(40.0, float(pct_match.group(1)))
        else:
            market_decline = -10.0

    # 2. Interest Rate / RBI Repo Detection
    rate_match = re.search(r"(\d+)\s*(bps|basis\s*points)", prompt_lower)
    if rate_match:
        val = int(rate_match.group(1))
        if any(w in prompt_lower for w in ["cut", "reduce", "lower", "ease"]):
            rate_change_bps = -min(200, val)
        else:
            rate_change_bps = min(300, val)
    elif "rate hike" in prompt_lower or "rbi hike" in prompt_lower or "raise rates" in prompt_lower:
        rate_change_bps = 75
    elif "rate cut" in prompt_lower or "ease" in prompt_lower:
        rate_change_bps = -50

    # 3. Currency / INR / USD Detection
    if any(k in prompt_lower for k in ["rupee drop", "rupee falls", "dollar surge", "dollar strengthens", "inr weakens"]):
        currency_shift = -5.0
    elif any(k in prompt_lower for k in ["rupee strengthens", "dollar drops"]):
        currency_shift = 4.0

    # 4. Sector-Specific Shocks
    if any(k in prompt_lower for k in ["tech", "software", "it sector", "us spending freeze"]):
        sector_shocks["IT"] = -25.0
    if any(k in prompt_lower for k in ["bank", "nbfc", "credit", "npa", "bad loans"]):
        sector_shocks["Banking"] = -15.0
    if any(k in prompt_lower for k in ["real estate", "property", "reit", "housing slump"]):
        sector_shocks["Real Estate"] = -18.0
    if any(k in prompt_lower for k in ["gold rally", "safe haven", "inflation"]):
        sector_shocks["Gold"] = 8.0
    if any(k in prompt_lower for k in ["energy", "oil spike", "crude"]):
        sector_shocks["Energy"] = -12.0

    # Fallback default if completely empty
    if market_decline == 0.0 and rate_change_bps == 0 and not sector_shocks:
        market_decline = -15.0
        rate_change_bps = 75
        sector_shocks["IT"] = -25.0
        sector_shocks["Banking"] = -10.0
        sector_shocks["Gold"] = 8.0
        currency_shift = -5.0
        preset_name = "IT Sector Disruption + RBI Rate Hike"

    return {
        "preset_name": preset_name,
        "market_decline_pct": round(market_decline, 1),
        "interest_rate_change_bps": rate_change_bps,
        "sector_shocks": sector_shocks,
        "currency_inr_usd_shift_pct": round(currency_shift, 1),
        "custom_ai_prompt": custom_prompt,
    }


def diagnose_financial_trilemma(
    total_val: float,
    target_goal: float,
    horizon_yrs: float,
    risk_tol: str,
) -> List[Dict[str, str]]:
    """
    Diagnoses the Impossible Trinity of Investing:
    Target Return <-> Time Horizon <-> Risk Tolerance.
    When a user demands returns that are mathematically unachievable for their risk tolerance,
    surfaces the exact 3 actionable levers (Capital, Horizon, or Tail Risk).
    """
    if total_val <= 0 or target_goal <= total_val or horizon_yrs <= 0:
        return []

    # Required Compound Annual Growth Rate (CAGR)
    cagr_required = (math.pow(target_goal / total_val, 1.0 / horizon_yrs) - 1.0) * 100.0

    # Maximum safe yield achievable for investor's risk tolerance
    risk_tol_lower = risk_tol.lower()
    if risk_tol_lower == "low":
        max_safe_yield = 7.0   # Liquid debt, FDs, arbitrage
    elif risk_tol_lower == "moderate":
        max_safe_yield = 10.5  # Balanced hybrid, multi-asset
    else:
        max_safe_yield = 14.0  # Pure equity alpha

    trilemma_conflicts: List[Dict[str, str]] = []

    if cagr_required > max_safe_yield:
        # 1. Fresh Capital needed today to hit goal at safe yield
        safe_r = max_safe_yield / 100.0
        present_value_needed = target_goal / math.pow(1.0 + safe_r, horizon_yrs)
        capital_gap = int(round(present_value_needed - total_val))

        # 2. Horizon extension needed at safe yield
        extended_years = round(math.log(target_goal / total_val) / math.log(1.0 + safe_r), 1)

        msg = (
            f"Financial Trilemma Conflict: Hitting your ₹{int(target_goal):,} goal from ₹{int(total_val):,} "
            f"in {int(horizon_yrs)} year(s) demands a +{cagr_required:.1f}% annual return, but your Low risk tolerance "
            f"caps safe yields at ~{max_safe_yield}%. Mathematical Levers to resolve this: "
            f"(1) Add ₹{capital_gap:,} fresh capital today, (2) Extend horizon to {extended_years} years, "
            f"or (3) Accept high-beta equity volatility risking a ₹2,00,000+ crash loss."
        )
        trilemma_conflicts.append({
            "severity": "HIGH",
            "type": "FINANCIAL_TRILEMMA_BREACH",
            "message": msg,
        })

    return trilemma_conflicts


def generate_ai_insights(
    portfolio: Dict[str, Any],
    quant_results: Dict[str, Any],
    custom_prompt: str = ""
) -> Dict[str, Any]:
    """
    Evaluates investor profile against quantitative results to identify goal/liquidity conflicts,
    transparent mathematical assumptions, transmission spillovers, and rebalancing trade-offs.
    """
    portfolio = portfolio or {}
    quant_results = quant_results or {}
    custom_prompt = custom_prompt or ""

    if "portfolio" in portfolio and isinstance(portfolio["portfolio"], dict):
        base = portfolio["portfolio"]
    else:
        base = portfolio

    profile = base.get("investor_profile", {}) if isinstance(base, dict) else {}
    horizon_yrs = float(profile.get("horizon_years", 3) or 3)
    risk_tol = str(profile.get("risk_tolerance", "Moderate") or "Moderate")
    liq_need = str(profile.get("liquidity_need", "Medium") or "Medium").lower()
    target_goal = float(profile.get("target_goal_inr", 1000000) or 1000000)

    summary = quant_results.get("summary", {})
    total_val = float(summary.get("total_value_inr", 1000000))
    stressed_val = float(summary.get("stressed_value_median_inr", total_val))
    impact_pct = float(summary.get("estimated_impact_pct", 0.0))
    illiquid_share = float(summary.get("illiquid_ share_pct", summary.get("illiquid_share_pct", 0.0)))

    composition = quant_results.get("composition", {})
    sectors = composition.get("by_sector", [])

    conflicts: List[Dict[str, str]] = []

    # 1. Financial Trilemma Diagnosis (The Root of Goal Conflicts)
    trilemma_alerts = diagnose_financial_trilemma(total_val, target_goal, horizon_yrs, risk_tol)
    conflicts.extend(trilemma_alerts)

    # 2. Time Horizon vs Equity Volatility Conflict
    equity_sectors = ["IT", "Banking", "Energy", "Healthcare", "Consumer", "Real Estate"]
    equity_weight = sum(s.get("weight_pct", 0.0) for s in sectors if s.get("sector") in equity_sectors)

    if horizon_yrs <= 2 and equity_weight > 50.0:
        conflicts.append({
            "severity": "HIGH",
            "type": "HORIZON_VS_VOLATILITY",
            "message": (
                f"Your investment horizon is only {int(horizon_yrs)} year(s) with {risk_tol} risk tolerance, "
                f"but {equity_weight:.0f}% of your capital is committed to volatile equity sectors."
            ),
        })

    # 3. Liquidity Cascade Trap: Illiquid Assets Forcing Liquid Asset Fire-Sale
    if liq_need == "high" and illiquid_share > 5.0:
        conflicts.append({
            "severity": "MEDIUM",
            "type": "LIQUIDITY_MISMATCH",
            "message": (
                f"Liquidity Cascade Risk: You marked Liquidity Need as High, but {illiquid_share:.1f}% "
                f"of your capital is locked in illiquid debt/REITs. In a cash crunch, this locked allocation "
                f"forces a fire-sale of your crashed equities at a steep loss to raise cash."
            ),
        })

    # 4. Risk Tolerance Drawdown Breach
    if risk_tol.lower() == "low" and impact_pct < -12.0:
        conflicts.append({
            "severity": "HIGH",
            "type": "RISK_TOLERANCE_BREACH",
            "message": (
                f"Simulated portfolio drawdown of {impact_pct}% under this stress test severely exceeds "
                f"a Low risk tolerance threshold (-10% max capital preservation buffer)."
            ),
        })

    # 5. False Diversification Warning from Correlation Matrix
    corr_matrix = quant_results.get("correlation_matrix", {})
    high_corr_warn = corr_matrix.get("high_correlation_warning", "")
    if high_corr_warn:
        conflicts.append({
            "severity": "MEDIUM",
            "type": "FALSE_DIVERSIFICATION",
            "message": high_corr_warn,
        })

    # Build Assumptions Used Array incorporating Deterministic Transmission Notes
    assumptions: List[str] = [
        "Broad market declines applied using sectoral beta sensitivity relative to the Nifty 50 benchmark.",
        "Factor Transmission Matrix: Modeled second-order spillovers (DCF growth stock multiple compression & bank MTM markdowns).",
        "Monte Carlo projection cone incorporates 500 stochastic paths over a 3-year historical covariance window.",
        "Probabilistic cones reflect 10th-90th percentile bands; hypothetical outcomes are not guaranteed future returns.",
    ]

    # Incorporate specific transmission spillover notes from quant engine
    spillover_notes = quant_results.get("_spillover_notes", [])
    for note in spillover_notes:
        assumptions.append(f"Transmission Channel: {note}")

    if custom_prompt:
        assumptions.insert(0, f"Scenario parameters derived from user query: '{custom_prompt}'.")

    alt_portfolio = quant_results.get("alternative_portfolio", {
        "name": "AI Risk-Adjusted Hedge Allocation",
        "proposed_assets": [],
        "stressed_value_median_inr": int(stressed_val),
        "drawdown_saved_inr": 0,
        "tradeoff_explanation": "Protects downside capital by shifting concentrated equities into defensive hedges.",
    })

    return {
        "assumptions_used": assumptions,
        "goal_conflicts": conflicts,
        "alternative_portfolio": alt_portfolio,
    }
