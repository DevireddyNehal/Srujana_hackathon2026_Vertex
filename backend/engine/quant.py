"""Portfolio risk and scenario engine for the Srujana F-06 demo.

This module intentionally uses only the Python standard library. Because the
hackathon mock portfolios do not include verified historical price series,
correlations, or expected returns, it uses transparent *demo assumptions*.
Generated chart observations are synthetic and must not be described as actual
NSE history.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any


SECTOR_CONCENTRATION_PENALTY_POINTS = 20
HISTORICAL_RELATIVE_VALUES = (
    0.92, 0.95, 0.93, 0.96, 0.98, 0.97, 0.99,
    1.01, 0.98, 1.02, 1.01, 1.03, 1.00,
)
DEFAULT_ANNUAL_DRIFT = 0.05
P10_Z = -1.2815515655446004
P90_Z = 1.2815515655446004


def _number(value: Any, default: float = 0.0) -> float:
    """Convert a value to a finite float, returning default otherwise."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _round_money(value: float) -> int:
    return int(round(value))


def _get_assets(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    raw_assets = portfolio.get("assets")
    if not isinstance(raw_assets, list) or not raw_assets:
        raise ValueError("portfolio.assets must be a non-empty list")

    assets: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_assets):
        if not isinstance(raw, dict):
            raise ValueError(f"portfolio.assets[{index}] must be an object")
        amount = _number(raw.get("amount_inr"), default=-1.0)
        if amount <= 0:
            raise ValueError(
                f"portfolio.assets[{index}].amount_inr must be a positive number"
            )
        asset = dict(raw)
        asset["ticker"] = str(raw.get("ticker") or f"ASSET_{index + 1}")
        asset["name"] = str(raw.get("name") or asset["ticker"])
        asset["sector"] = str(raw.get("sector") or "Other")
        asset["asset_class"] = str(raw.get("asset_class") or "Other")
        asset["liquidity_tag"] = str(raw.get("liquidity_tag") or "Medium").title()
        if asset["liquidity_tag"] not in {"High", "Medium", "Low"}:
            asset["liquidity_tag"] = "Medium"
        asset["currency_exposure"] = str(raw.get("currency_exposure") or "INR")
        asset["amount_inr"] = amount
        assets.append(asset)
    return assets


def _normalize_scenario(scenario_shocks: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize contract/frontend aliases and clamp shocks to documented bounds."""
    scenario = scenario_shocks if isinstance(scenario_shocks, dict) else {}

    market = scenario.get("market_decline_pct")
    if market is None:
        market = scenario.get("market_drop_pct", scenario.get("market_shock_pct", 0.0))
    market_pct = _clamp(_number(market), -50.0, 0.0)

    rate = scenario.get("interest_rate_change_bps", scenario.get("rate_change_bps", 0.0))
    rate_bps = _clamp(_number(rate), -100.0, 300.0)

    raw_sector_shocks = scenario.get("sector_shocks", {})
    sectors: dict[str, float] = {}
    if isinstance(raw_sector_shocks, dict):
        for sector, shock in raw_sector_shocks.items():
            sectors[str(sector).strip().casefold()] = _clamp(_number(shock), -100.0, 100.0)

    fx = scenario.get("currency_inr_usd_shift_pct")
    if fx is None:
        fx = scenario.get("currency_shift_pct", scenario.get("fx_shift_pct", 0.0))
    fx_pct = _clamp(_number(fx), -15.0, 15.0)

    return {
        "market_decline_pct": market_pct,
        "interest_rate_change_bps": rate_bps,
        "sector_shocks": sectors,
        "currency_inr_usd_shift_pct": fx_pct,
        "preset_name": str(scenario.get("preset_name") or "Custom scenario"),
    }


def _sector_shock_for(sector: str, shocks: dict[str, float]) -> float:
    sector_key = sector.casefold()
    if sector_key in shocks:
        return shocks[sector_key]
    # Small aliases help when the UI uses common alternate labels.
    aliases = {
        "information technology": "it",
        "technology": "it",
        "banks": "banking",
        "financials": "banking",
        "consumer staples": "fmcg",
        "realty": "real estate",
    }
    for alias, canonical in aliases.items():
        if sector_key == alias and canonical in shocks:
            return shocks[canonical]
    return 0.0


def _is_debt(asset: dict[str, Any]) -> bool:
    asset_class = asset["asset_class"].casefold()
    return any(term in asset_class for term in ("debt", "bond", "fixed income"))


def _market_beta(asset: dict[str, Any]) -> float:
    if not _is_debt(asset) and asset["asset_class"].casefold() not in {"commodity", "gold"}:
        sector = asset["sector"].casefold()
        if sector == "it" or "technology" in sector:
            return 1.15
        if sector in {"banking", "financials", "banks"}:
            return 1.25
        if sector == "fmcg" or "consumer" in sector:
            return 0.80
        if "real estate" in sector or "realty" in sector:
            return 1.00
        return 1.00
    if asset["sector"].casefold() == "gold" or asset["asset_class"].casefold() in {"commodity", "gold"}:
        return -0.10
    return 0.0


def _duration_years(asset: dict[str, Any]) -> float:
    """Demo duration/sensitivity assumption; not instrument-specific research."""
    if _is_debt(asset):
        ticker = asset["ticker"].upper()
        sector = asset["sector"].casefold()
        name = asset["name"].casefold()
        if "liquid" in ticker or "liquid" in sector or "short-duration" in name:
            return 0.1
        if "government" in sector or "gsec" in ticker or "10-year" in name or "10 year" in name:
            return 4.5
        if "corporate bond" in sector or "corporate bond" in name:
            return 3.5
        return 3.0
    sector = asset["sector"].casefold()
    if sector in {"banking", "financials", "banks"}:
        return 1.0
    if "real estate" in sector or "realty" in sector:
        return 2.0
    return 0.0


def _fx_gamma(asset: dict[str, Any]) -> float:
    exposure = asset["currency_exposure"].upper()
    if "USD" not in exposure:
        return 0.0
    sector = asset["sector"].casefold()
    if sector == "it" or "technology" in sector:
        return 0.50
    return 0.20


def _annual_volatility(asset: dict[str, Any]) -> float:
    """Return an assumed annual volatility as a decimal fraction."""
    sector = asset["sector"].casefold()
    name = asset["name"].casefold()
    ticker = asset["ticker"].upper()
    if "liquid" in ticker or "liquid" in sector or "short-duration" in name:
        return 0.02
    if _is_debt(asset):
        if "government" in sector or "gsec" in ticker or "10-year" in name or "10 year" in name:
            return 0.08
        if "corporate" in sector or "corporate" in name:
            return 0.06
        return 0.07
    if sector == "it" or "technology" in sector:
        return 0.30
    if sector in {"banking", "financials", "banks"}:
        return 0.25
    if sector == "gold" or asset["asset_class"].casefold() in {"commodity", "gold"}:
        return 0.15
    if sector == "fmcg" or "consumer" in sector:
        return 0.18
    if "real estate" in sector or "realty" in sector:
        return 0.20
    if "diversified equity" in sector:
        return 0.20
    return 0.18


def _correlation(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Transparent demo correlation proxy; not calculated from actual returns."""
    if a["ticker"] == b["ticker"]:
        return 1.0
    sa, sb = a["sector"].casefold(), b["sector"].casefold()
    ca, cb = a["asset_class"].casefold(), b["asset_class"].casefold()
    gold_a = sa == "gold" or ca in {"commodity", "gold"}
    gold_b = sb == "gold" or cb in {"commodity", "gold"}
    debt_a, debt_b = _is_debt(a), _is_debt(b)

    if {a["ticker"].upper(), b["ticker"].upper()} == {"TCS.NS", "INFY.NS"}:
        return 0.88
    if sa == sb:
        return 0.88 if sa == "it" else 0.65
    if gold_a and gold_b:
        return 0.70
    if gold_a or gold_b:
        return -0.10 if not (debt_a or debt_b) else 0.05
    if debt_a and debt_b:
        return 0.45
    if debt_a or debt_b:
        return 0.15
    if ca == cb:
        return 0.35
    return 0.25


def _make_correlation_matrix(assets: list[dict[str, Any]]) -> dict[str, Any]:
    matrix: list[list[float]] = []
    for i, a in enumerate(assets):
        row: list[float] = []
        for j, b in enumerate(assets):
            value = 1.0 if i == j else _correlation(a, b)
            row.append(round(_clamp(value, -1.0, 1.0), 2))
        matrix.append(row)

    warnings: list[str] = []
    for i in range(len(assets)):
        for j in range(i + 1, len(assets)):
            corr = matrix[i][j]
            if corr > 0.75:
                warnings.append(
                    f"{assets[i]['ticker']} and {assets[j]['ticker']} have an "
                    f"assumed correlation of {corr:.2f}; this demo proxy may indicate "
                    "shared exposure rather than genuine diversification."
                )
    return {
        "tickers": [asset["ticker"] for asset in assets],
        "matrix": matrix,
        "high_correlation_warning": " ".join(warnings) if warnings else None,
        "data_status": "Assumption-based demo estimates; not calculated from historical returns.",
    }


def _weighted_volatility(assets: list[dict[str, Any]], total: float) -> float:
    if total <= 0:
        return 0.0
    weights = [asset["amount_inr"] / total for asset in assets]
    vols = [_annual_volatility(asset) for asset in assets]
    variance = 0.0
    for i, asset_i in enumerate(assets):
        for j, asset_j in enumerate(assets):
            rho = 1.0 if i == j else _correlation(asset_i, asset_j)
            variance += weights[i] * weights[j] * vols[i] * vols[j] * rho
    return math.sqrt(max(0.0, variance))


def _composition(assets: list[dict[str, Any]], total: float) -> dict[str, Any]:
    sector_values: dict[str, float] = {}
    class_values: dict[str, float] = {}
    liquidity_values = {"High": 0.0, "Medium": 0.0, "Low": 0.0}
    equity_total = 0.0
    equity_by_sector: dict[str, float] = {}
    hhi = 0.0

    for asset in assets:
        amount = asset["amount_inr"]
        sector = asset["sector"]
        asset_class = asset["asset_class"]
        sector_values[sector] = sector_values.get(sector, 0.0) + amount
        class_values[asset_class] = class_values.get(asset_class, 0.0) + amount
        liquidity_values[asset["liquidity_tag"]] += amount
        hhi += (amount / total) ** 2
        if asset_class.casefold() in {"equity", "stock", "stocks"}:
            equity_total += amount
            equity_by_sector[sector] = equity_by_sector.get(sector, 0.0) + amount

    by_sector = [
        {"sector": sector, "weight_pct": round(amount / total * 100.0, 2)}
        for sector, amount in sorted(sector_values.items(), key=lambda item: (-item[1], item[0]))
    ]
    by_asset_class = [
        {"asset_class": asset_class, "weight_pct": round(amount / total * 100.0, 2)}
        for asset_class, amount in sorted(class_values.items(), key=lambda item: (-item[1], item[0]))
    ]
    by_liquidity = {
        tag: round(amount / total * 100.0, 2)
        for tag, amount in liquidity_values.items()
    }

    count = len(assets)
    if count <= 1:
        score = 0.0
    else:
        score = 100.0 * (1.0 - ((hhi - 1.0 / count) / (1.0 - 1.0 / count)))
        score = _clamp(score, 0.0, 100.0)

    max_equity_sector_share = (
        max(equity_by_sector.values()) / equity_total if equity_total > 0 and equity_by_sector else 0.0
    )
    sector_penalty_applied = max_equity_sector_share >= 0.60
    if sector_penalty_applied:
        score = max(0.0, score - SECTOR_CONCENTRATION_PENALTY_POINTS)

    illiquid_share_pct = by_liquidity["Low"]
    return {
        "by_sector": by_sector,
        "by_asset_class": by_asset_class,
        "by_liquidity": by_liquidity,
        "concentration_hhi": round(hhi, 4),
        "diversification_score_out_of_100": int(round(score)),
        "illiquid_share_pct": round(illiquid_share_pct, 2),
        "equity_sector_concentration_pct": round(max_equity_sector_share * 100.0, 2),
        "sector_concentration_penalty_applied": sector_penalty_applied,
    }


def _asset_stress_return_pct(asset: dict[str, Any], scenario: dict[str, Any]) -> float:
    """Additive linear sensitivity model; output is a percentage return."""
    market_effect = _market_beta(asset) * scenario["market_decline_pct"]
    sector_effect = _sector_shock_for(asset["sector"], scenario["sector_shocks"])
    # bps / 100 converts rate change into percentage points before duration scaling.
    rate_effect = -_duration_years(asset) * scenario["interest_rate_change_bps"] / 100.0
    fx_effect = _fx_gamma(asset) * scenario["currency_inr_usd_shift_pct"]
    return _clamp(market_effect + sector_effect + rate_effect + fx_effect, -95.0, 100.0)


def _stressed_value(assets: list[dict[str, Any]], scenario: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
    total = 0.0
    details: list[dict[str, Any]] = []
    for asset in assets:
        return_pct = _asset_stress_return_pct(asset, scenario)
        stressed_value = asset["amount_inr"] * (1.0 + return_pct / 100.0)
        total += stressed_value
        details.append({
            "ticker": asset["ticker"],
            "sector": asset["sector"],
            "starting_amount_inr": _round_money(asset["amount_inr"]),
            "scenario_return_pct": round(return_pct, 2),
            "stressed_value_inr": _round_money(stressed_value),
        })
    return total, details


def _subtract_months(year: int, month: int, offset: int) -> tuple[int, int]:
    absolute = year * 12 + (month - 1) - offset
    return absolute // 12, absolute % 12 + 1


def _add_months(year: int, month: int, offset: int) -> tuple[int, int]:
    absolute = year * 12 + (month - 1) + offset
    return absolute // 12, absolute % 12 + 1


def _month_label(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _synthetic_history(total_value: float) -> list[dict[str, Any]]:
    """Create explicitly synthetic demo points; not historical market observations."""
    today = date.today()
    labels: list[str] = []
    for offset in range(12, -1, -1):
        year, month = _subtract_months(today.year, today.month, offset)
        labels.append(_month_label(year, month))
    return [
        {
            "month": label,
            "actual_value": _round_money(total_value * relative_value),
            "data_type": "synthetic_demo",
        }
        for label, relative_value in zip(labels, HISTORICAL_RELATIVE_VALUES)
    ]


def _max_drawdown_pct(series: list[dict[str, Any]]) -> float:
    peak = 0.0
    worst = 0.0
    for point in series:
        value = float(point["actual_value"])
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, (value / peak - 1.0) * 100.0)
    return round(worst, 2)


def _projection_cone(
    baseline_value: float,
    annual_volatility: float,
    start_year: int,
    start_month: int,
    rebalanced_baseline: float,
    rebalanced_volatility: float,
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    sigma = max(0.0, annual_volatility)
    alt_sigma = max(0.0, rebalanced_volatility)
    for month_ahead in range(1, 7):
        year, month = _add_months(start_year, start_month, month_ahead)
        t = month_ahead / 12.0
        median_multiplier = math.exp((DEFAULT_ANNUAL_DRIFT - 0.5 * sigma * sigma) * t)
        p10_multiplier = math.exp(
            (DEFAULT_ANNUAL_DRIFT - 0.5 * sigma * sigma) * t
            + sigma * math.sqrt(t) * P10_Z
        )
        p90_multiplier = math.exp(
            (DEFAULT_ANNUAL_DRIFT - 0.5 * sigma * sigma) * t
            + sigma * math.sqrt(t) * P90_Z
        )
        alt_median_multiplier = math.exp(
            (DEFAULT_ANNUAL_DRIFT - 0.5 * alt_sigma * alt_sigma) * t
        )
        points.append({
            "month": _month_label(year, month),
            "p10_worst_case": _round_money(baseline_value * p10_multiplier),
            "p50_median_case": _round_money(baseline_value * median_multiplier),
            "p90_best_case": _round_money(baseline_value * p90_multiplier),
            "rebalanced_p50": _round_money(rebalanced_baseline * alt_median_multiplier),
            "data_type": "hypothetical_simulation",
        })
    return points


def _alternative_assets(total: float) -> list[dict[str, Any]]:
    """Simple defensive demo allocation; not individualized investment advice."""
    allocation = [
        ("NIFTYBEES.NS", "Nifty 50 ETF (Demo Holding)", "Diversified Equity", "Equity", 25.0, "High", "INR"),
        ("HDFCBANK.NS", "HDFC Bank (Demo Holding)", "Banking", "Equity", 10.0, "High", "INR"),
        ("ITC.NS", "ITC Ltd (Demo Holding)", "FMCG", "Equity", 15.0, "High", "INR"),
        ("GOLDBEES.NS", "Gold ETF (Demo Holding)", "Gold", "Commodity", 20.0, "High", "INR"),
        ("LIQUIDBEES.NS", "Liquid ETF / Short-Duration Debt (Demo Holding)", "Liquid Debt", "Debt", 25.0, "High", "INR"),
        ("GSEC10Y_MOCK", "10-Year Government Securities (Demo Asset)", "Government Bonds", "Debt", 5.0, "Medium", "INR"),
    ]
    assets: list[dict[str, Any]] = []
    for ticker, name, sector, asset_class, weight, liquidity, currency in allocation:
        assets.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "asset_class": asset_class,
            "weight_pct": weight,
            "amount_inr": total * weight / 100.0,
            "liquidity_tag": liquidity,
            "currency_exposure": currency,
        })
    return assets


def run_portfolio_scenario(portfolio: dict[str, Any], scenario_shocks: dict[str, Any]) -> dict[str, Any]:
    """Analyze a portfolio under a hypothetical stress scenario.

    Args:
        portfolio: Mapping with ``investor_profile`` and a non-empty ``assets`` list.
        scenario_shocks: Scenario mapping. Supports the frontend contract fields
            ``market_decline_pct``, ``interest_rate_change_bps``, ``sector_shocks``,
            and ``currency_inr_usd_shift_pct`` as well as documented aliases.

    Returns a JSON-serializable dictionary containing contract-level fields plus
    convenience fields for the sample API response.
    """
    if not isinstance(portfolio, dict):
        raise ValueError("portfolio must be an object")

    assets = _get_assets(portfolio)
    total = sum(asset["amount_inr"] for asset in assets)
    if total <= 0:
        raise ValueError("portfolio total must be greater than zero")
    scenario = _normalize_scenario(scenario_shocks)

    composition = _composition(assets, total)
    correlations = _make_correlation_matrix(assets)
    volatility = _weighted_volatility(assets, total)
    stressed_value, asset_impacts = _stressed_value(assets, scenario)
    impact_inr = stressed_value - total
    impact_pct = (impact_inr / total * 100.0) if total else 0.0

    history = _synthetic_history(total)
    max_drawdown = _max_drawdown_pct(history)

    alternative_assets = _alternative_assets(total)
    alternative_stressed, _ = _stressed_value(alternative_assets, scenario)
    alternative_volatility = _weighted_volatility(alternative_assets, total)
    drawdown_saved = alternative_stressed - stressed_value

    today = date.today()
    cone = _projection_cone(
        baseline_value=stressed_value,
        annual_volatility=volatility,
        start_year=today.year,
        start_month=today.month,
        rebalanced_baseline=alternative_stressed,
        rebalanced_volatility=alternative_volatility,
    )

    profile = portfolio.get("investor_profile") if isinstance(portfolio.get("investor_profile"), dict) else {}
    target = _number(profile.get("target_goal_inr"), total)
    assumptions = [
        f"Applied a broad-market shock of {scenario['market_decline_pct']:.2f}% with assumed sector betas.",
        f"Applied a {scenario['interest_rate_change_bps']:.0f} bps rate change using demo duration/sensitivity assumptions.",
        "Combined market, sector, rate and FX effects additively; each asset return is bounded between -95% and +100%.",
        "Correlations and annual volatilities are illustrative sector/asset-class proxies, not computed from verified historical returns.",
        f"Projection cone uses a constant assumed annual drift of {DEFAULT_ANNUAL_DRIFT * 100:.1f}% and a lognormal percentile approximation.",
        "The historical-looking chart series is synthetic demo data, not actual NSE history.",
        f"Diversification score follows normalized holding HHI; a {SECTOR_CONCENTRATION_PENALTY_POINTS}-point penalty is applied when one sector exceeds 60% of equity holdings.",
        "Alternative allocation is a heuristic comparison, not individualized investment advice or a guaranteed hedge.",
    ]
    if scenario["currency_inr_usd_shift_pct"]:
        assumptions.append(
            "FX assumption: a positive INR-per-USD shift means USD strengthens against INR; exporter exposure may benefit."
        )

    summary = {
        "total_value_inr": _round_money(total),
        "target_goal_inr": _round_money(target),
        "stressed_value_median_inr": _round_money(stressed_value),
        "estimated_impact_inr": _round_money(impact_inr),
        "estimated_impact_pct": round(impact_pct, 2),
        "annualized_volatility_pct": round(volatility * 100.0, 2),
        "max_drawdown_pct": max_drawdown,
        "diversification_score_out_of_100": composition["diversification_score_out_of_100"],
        "illiquid_share_pct": composition["illiquid_share_pct"],
    }

    alternative_portfolio = {
        "name": "Heuristic Risk-Adjusted Alternative (Demo)",
        "proposed_assets": [
            {
                "ticker": asset["ticker"],
                "name": asset["name"],
                "sector": asset["sector"],
                "asset_class": asset["asset_class"],
                "weight_pct": asset["weight_pct"],
                "amount_inr": _round_money(asset["amount_inr"]),
            }
            for asset in alternative_assets
        ],
        "stressed_value_median_inr": _round_money(alternative_stressed),
        "drawdown_saved_inr": _round_money(drawdown_saved),
        "tradeoff_explanation": (
            f"Under this selected scenario, the alternative's modeled stressed value is "
            f"₹{_round_money(alternative_stressed):,} versus ₹{_round_money(stressed_value):,} "
            f"for the current allocation (difference ₹{_round_money(drawdown_saved):,}). "
            "This is a scenario-specific model comparison, not a guaranteed loss reduction. "
            "No annual upside-forgone estimate is made because verified expected-return inputs were not supplied."
        ),
        "data_status": "Illustrative allocation for comparison; not individualized investment advice.",
    }

    chart_data = {
        "disclaimer": (
            "Historical-looking points are synthetic demonstration data, not verified past NSE observations. "
            "The forward P10/P50/P90 values are hypothetical model outputs, depend on stated assumptions, "
            "and are not guaranteed results."
        ),
        "historical_observations": history,
        "hypothetical_projection_cone": cone,
    }

    risk_metrics = {
        "annualized_volatility_pct": round(volatility * 100.0, 2),
        "max_drawdown_pct": max_drawdown,
        "max_drawdown_data_status": "Computed only from synthetic demo history; not a real historical drawdown.",
        "diversification_score_out_of_100": composition["diversification_score_out_of_100"],
        "concentration_hhi": composition["concentration_hhi"],
        "illiquid_share_pct": composition["illiquid_share_pct"],
        "equity_sector_concentration_pct": composition["equity_sector_concentration_pct"],
        "scenario_impact_pct": round(impact_pct, 2),
    }

    return {
        # API/demo convenience fields
        "summary": summary,
        "composition": composition,
        "correlation_matrix": correlations,
        "chart_data": chart_data,
        "alternative_portfolio": alternative_portfolio,
        "assumptions_used": assumptions,
        # Contract-level engine fields
        "risk_metrics": risk_metrics,
        "historical_series": history,
        "hypothetical_cone": cone,
        "asset_impacts": asset_impacts,
        "scenario_applied": scenario,
        "data_status": "Demo estimates only; no live or verified historical market feed is used.",
    }
