"""Scenario-text parser and deterministic portfolio guardrails for Srujana F-06.

This module requires no hosted AI service or API key. It uses transparent rules
so demo behavior is repeatable and auditable. The parser is intentionally a
lightweight heuristic, not a general-purpose financial language model.
"""

from __future__ import annotations

import re
from typing import Any


_NUMBER = r"[-+]?\d+(?:\.\d+)?"
_PERCENT_RE = re.compile(rf"(?P<value>{_NUMBER})\s*(?:%|percent(?:age)?)", re.IGNORECASE)
_BPS_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?:bps\b|basis\s+points?\b)", re.IGNORECASE)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _num(text: str, default: float = 0.0) -> float:
    try:
        value = float(text)
    except (ValueError, TypeError):
        return default
    return value if value == value and abs(value) != float("inf") else default


def _has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    """Match directional stems as words, so 'against' does not match 'gain'."""
    return any(re.search(rf"\b{re.escape(term)}\w*\b", text, re.IGNORECASE) for term in terms)


def _find_market_shock(prompt: str) -> float:
    patterns = [
        re.compile(
            rf"(?:market|nifty(?:\s*50)?|equities|stocks?)\b.{{0,45}}?"
            rf"(?P<verb>drop(?:s|ped)?|declin(?:e|es|ed)|fall(?:s|en)?|crash(?:es|ed)?|"
            rf"sell[- ]?off|down|plung(?:e|es|ed)|collaps(?:e|es|ed))"
            rf".{{0,18}}?(?:by\s*)?(?P<value>{_NUMBER})\s*(?:%|percent)",
            re.IGNORECASE,
        ),
        re.compile(
            rf"(?P<value>{_NUMBER})\s*(?:%|percent).{{0,20}}?"
            rf"(?:market|nifty(?:\s*50)?|equities|stocks?).{{0,25}}?"
            rf"(?P<verb>drop|declin|fall|crash|down|plung|collaps)",
            re.IGNORECASE,
        ),
    ]
    for pattern in patterns:
        match = pattern.search(prompt)
        if not match:
            continue
        value = _num(match.group("value"))
        verb = match.group("verb").casefold()
        if value > 0 or verb in {"drop", "drops", "dropped", "decline", "declines", "declined", "fall", "falls", "fallen", "crash", "crashes", "crashed", "sell-off", "down", "plunge", "plunges", "plunged", "collapse", "collapses", "collapsed"}:
            return -abs(value)
        return value
    return 0.0


def _find_rate_change(prompt: str) -> float:
    match = _BPS_RE.search(prompt)
    if not match:
        return 0.0
    value = abs(_num(match.group("value")))
    before = prompt[max(0, match.start() - 70):match.start()].casefold()
    after = prompt[match.end():match.end() + 35].casefold()
    decrease_terms = ("cut", "cuts", "cutting", "lower", "lowers", "lowered", "reduce", "reduces", "reduced", "decrease", "decreases", "decreased", "easing")
    increase_terms = ("hike", "hikes", "hiked", "raise", "raises", "raised", "increase", "increases", "increased", "tighten", "tightens", "tightened")
    if any(term in before or term in after for term in decrease_terms):
        value = -value
    elif any(term in before or term in after for term in increase_terms):
        value = value
    return _clamp(value, -100.0, 300.0)


def _direction_from_context(value: float, context: str, default_negative: bool = False) -> float:
    text = context.casefold()
    if value < 0:
        return -abs(value)
    positive = ("rise", "rises", "rose", "gain", "gains", "gained", "surge", "surges", "up", "increase", "increases", "increased", "strengthen", "strengthens", "strengthened", "appreciate", "appreciates", "appreciated", "grow", "grows", "grew")
    negative = ("drop", "drops", "dropped", "decline", "declines", "declined", "fall", "falls", "fell", "crash", "crashes", "crashed", "down", "lose", "loses", "lost", "plunge", "plunges", "plunged", "collapse", "collapses", "collapsed", "weaken", "weakens", "weakened", "depreciate", "depreciates", "depreciated")
    has_positive = any(term in text for term in positive)
    has_negative = any(term in text for term in negative)
    if has_negative and not has_positive:
        return -abs(value)
    if has_positive and not has_negative:
        return abs(value)
    return -abs(value) if default_negative else abs(value)


def _find_sector_shocks(prompt: str) -> dict[str, float]:
    """Extract explicit or common keyword-based shocks for supported sectors."""
    aliases: list[tuple[str, str]] = [
        ("information technology", "IT"),
        ("consumer staples", "FMCG"),
        ("technology", "IT"),
        ("real estate", "Real Estate"),
        ("reits", "Real Estate"),
        ("reit", "Real Estate"),
        ("banking", "Banking"),
        ("banks", "Banking"),
        ("bank", "Banking"),
        ("fmcg", "FMCG"),
        ("technology", "IT"),
        ("tech", "IT"),
        ("gold", "Gold"),
        ("it", "IT"),
        ("realty", "Real Estate"),
    ]
    # The longer aliases are considered first to avoid partial-word matches.
    aliases.sort(key=lambda pair: len(pair[0]), reverse=True)
    lower_prompt = prompt.casefold()
    found: dict[str, float] = {}
    claimed_spans: list[tuple[int, int]] = []

    negative_terms = (
        "drop", "declin", "fall", "crash", "down", "plung", "collaps", "lose", "loss",
        "disrupt", "freeze", "freezes", "frozen", "slump", "sell-off", "weaken", "disruption",
    )
    positive_terms = (
        "rise", "gain", "surge", "up", "increase", "strengthen", "appreciate", "grow", "rebound",
    )
    default_shocks = {"IT": -20.0, "Banking": -15.0, "Real Estate": -15.0, "FMCG": -10.0, "Gold": 8.0}

    for alias, canonical in aliases:
        pattern = re.compile(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", re.IGNORECASE)
        for match in pattern.finditer(lower_prompt):
            if any(start <= match.start() < end for start, end in claimed_spans):
                continue
            claimed_spans.append((match.start(), match.end()))

            # Prefer the sentence/phrase after the sector name, stopping at a
            # comma/semicolon so a previous or following sector's percentage
            # is not accidentally assigned to this sector.
            after = prompt[match.end():]
            after = re.split(r"[,;\n]", after, maxsplit=1)[0][:70]
            percent_match = _PERCENT_RE.search(after)
            clause_start = max(
                prompt.rfind(",", 0, match.start()),
                prompt.rfind(";", 0, match.start()),
                prompt.rfind("\n", 0, match.start()),
            ) + 1
            clause_end_candidates = [
                position for position in (
                    prompt.find(",", match.end()),
                    prompt.find(";", match.end()),
                    prompt.find("\n", match.end()),
                ) if position >= 0
            ]
            clause_end = min(clause_end_candidates) if clause_end_candidates else len(prompt)
            context = prompt[clause_start:clause_end]

            # Also support wording such as "20% tech decline" where the percent
            # comes immediately before the sector label.
            if percent_match is None:
                before = prompt[max(0, match.start() - 45):match.start()]
                before_percent = list(_PERCENT_RE.finditer(before))
                if before_percent:
                    candidate = before_percent[-1]
                    gap = before[candidate.end():]
                    if len(gap) <= 24 and any(term in gap.casefold() for term in negative_terms + positive_terms):
                        percent_match = candidate
                        context = before + prompt[match.start():min(len(prompt), match.end() + 25)]

            if percent_match is not None:
                raw_value = percent_match.group("value")
                value = _num(raw_value)
                shock_context = context.casefold()
                has_negative = _has_any_term(shock_context, negative_terms)
                has_positive = _has_any_term(shock_context, positive_terms)
                if value < 0:
                    shock = -abs(value)
                elif has_negative and not has_positive:
                    shock = -abs(value)
                elif has_positive and not has_negative:
                    shock = abs(value)
                elif raw_value.startswith("+"):
                    shock = abs(value)
                elif raw_value.startswith("-"):
                    shock = -abs(value)
                else:
                    # No direction words and no explicit sign: leave unparsed.
                    continue
                found[canonical] = _clamp(shock, -100.0, 100.0)
                continue

            # PLAN.md calls for a useful conservative default for plain-language
            # phrases like "tech spending freezes" with no numeric percentage.
            nearby = context.casefold()
            has_negative = _has_any_term(nearby, negative_terms)
            has_positive = _has_any_term(nearby, positive_terms)
            if has_negative and not has_positive:
                found[canonical] = default_shocks[canonical]
            elif has_positive and not has_negative:
                found[canonical] = abs(default_shocks[canonical])

    return found


def _find_currency_shift(prompt: str) -> float:
    currency_pattern = re.compile(r"\b(?:USD\s*/?\s*INR|INR\s*/?\s*USD|rupee(?:s)?|INR|USD|dollar(?:s)?)\b", re.IGNORECASE)
    match = currency_pattern.search(prompt)
    if not match:
        return 0.0

    # Prefer the same phrase as the currency mention; do not accidentally read a
    # market/sector percentage from an earlier clause.
    right = min(len(prompt), match.end() + 70)
    phrase_after = re.split(r"[,;\n]", prompt[match.end():right], maxsplit=1)[0]
    pct = _PERCENT_RE.search(phrase_after)
    context = prompt[max(0, match.start() - 45):match.end()] + " " + phrase_after
    if pct is None:
        phrase_before = re.split(r"[,;\n]", prompt[max(0, match.start() - 45):match.start()])[-1]
        before_percent = list(_PERCENT_RE.finditer(phrase_before))
        if before_percent and len(phrase_before[before_percent[-1].end():]) <= 22:
            pct = before_percent[-1]
            context = phrase_before + " " + context
    if pct is None:
        return 0.0

    value = _num(pct.group("value"))
    context_lower = context.casefold()
    # Positive means USD strengthens against INR / INR per USD rises.
    rupee_strength = any(re.search(pattern, context_lower) for pattern in (
        r"\brupee(?:s)?\s+strengthen\w*\b", r"\binr\s+strengthen\w*\b",
        r"\brupee(?:s)?\s+appreciat\w*\b", r"\binr\s+appreciat\w*\b",
        r"\brupee(?:s)?\s+ris\w*\b", r"\binr\s+ris\w*\b",
    ))
    usd_weakness = any(re.search(pattern, context_lower) for pattern in (
        r"\busd\s+weaken\w*\b", r"\bdollar(?:s)?\s+weaken\w*\b",
        r"\busd\s+depreciat\w*\b", r"\bdollar(?:s)?\s+depreciat\w*\b",
        r"\busd\s+fall\w*\b", r"\bdollar(?:s)?\s+fall\w*\b",
    ))
    usd_strength = any(re.search(pattern, context_lower) for pattern in (
        r"\busd\s+strengthen\w*\b", r"\bdollar(?:s)?\s+strengthen\w*\b",
        r"\busd\s+appreciat\w*\b", r"\bdollar(?:s)?\s+appreciat\w*\b",
        r"\busd\s+ris\w*\b", r"\bdollar(?:s)?\s+ris\w*\b",
        r"\brupee(?:s)?\s+weaken\w*\b", r"\binr\s+weaken\w*\b",
        r"\brupee(?:s)?\s+depreciat\w*\b", r"\binr\s+depreciat\w*\b",
    ))
    if value < 0:
        result = value  # Explicit signed value is treated as the direct INR-per-USD shift.
    elif rupee_strength or usd_weakness:
        result = -abs(value)
    elif usd_strength:
        result = abs(value)
    else:
        # A direct "USD/INR moves by 5%" is assumed to be a rise unless signed.
        result = value
    return _clamp(result, -15.0, 15.0)


def parse_custom_scenario(custom_prompt: str) -> dict[str, Any]:
    """Convert common scenario wording to bounded numeric shocks.

    Returns keys accepted by ``run_portfolio_scenario``. A missing parsed factor
    stays at zero so callers can safely merge these results with UI slider values.
    """
    prompt = custom_prompt if isinstance(custom_prompt, str) else ""
    market = _clamp(_find_market_shock(prompt), -50.0, 0.0)
    rate = _clamp(_find_rate_change(prompt), -100.0, 300.0)
    sectors = _find_sector_shocks(prompt)
    fx = _find_currency_shift(prompt)
    return {
        "market_decline_pct": round(market, 2),
        "interest_rate_change_bps": round(rate, 2),
        "sector_shocks": {key: round(value, 2) for key, value in sectors.items()},
        "currency_inr_usd_shift_pct": round(fx, 2),
        "source_prompt": prompt,
        "parser_note": (
            "Heuristic text extraction only. Review parsed shocks before running analysis; "
            "unrecognized wording may not be detected."
        ),
    }


def _asset_list(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    assets = portfolio.get("assets", []) if isinstance(portfolio, dict) else []
    return [asset for asset in assets if isinstance(asset, dict)] if isinstance(assets, list) else []


def _goal_conflicts(portfolio: dict[str, Any], quant_results: dict[str, Any]) -> list[dict[str, str]]:
    profile = portfolio.get("investor_profile", {}) if isinstance(portfolio, dict) else {}
    profile = profile if isinstance(profile, dict) else {}
    assets = _asset_list(portfolio)
    total = sum(max(0.0, _num(asset.get("amount_inr"))) for asset in assets)
    if total <= 0:
        return [{
            "severity": "HIGH",
            "type": "INVALID_PORTFOLIO_VALUE",
            "message": "The portfolio has no positive asset value to analyze. Check each amount_inr field.",
        }]

    equity_total = sum(
        max(0.0, _num(asset.get("amount_inr")))
        for asset in assets
        if str(asset.get("asset_class", "")).casefold() in {"equity", "stock", "stocks"}
    )
    equity_weight = equity_total / total * 100.0
    sector_totals: dict[str, float] = {}
    for asset in assets:
        sector = str(asset.get("sector") or "Other")
        sector_totals[sector] = sector_totals.get(sector, 0.0) + max(0.0, _num(asset.get("amount_inr")))
    max_sector_weight = max(sector_totals.values(), default=0.0) / total * 100.0
    illiquid_amount = sum(
        max(0.0, _num(asset.get("amount_inr")))
        for asset in assets
        if str(asset.get("liquidity_tag", "Medium")).casefold() == "low"
    )
    illiquid_share = illiquid_amount / total * 100.0

    summary = quant_results.get("summary", {}) if isinstance(quant_results, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    impact_pct = _num(summary.get("estimated_impact_pct", quant_results.get("risk_metrics", {}).get("scenario_impact_pct", 0.0) if isinstance(quant_results.get("risk_metrics"), dict) else 0.0))
    horizon = _num(profile.get("horizon_years"), default=99.0)
    tolerance = str(profile.get("risk_tolerance", "Unknown")).casefold()
    liquidity_need = str(profile.get("liquidity_need", "Medium")).casefold()

    conflicts: list[dict[str, str]] = []
    if horizon <= 2 and equity_weight > 50.0:
        conflicts.append({
            "severity": "HIGH",
            "type": "HORIZON_VS_VOLATILITY",
            "message": (
                f"The investment horizon is {horizon:g} year(s), while {equity_weight:.1f}% "
                "of portfolio value is held in equities. A short horizon can leave less time to recover from losses."
            ),
        })
    if liquidity_need == "high" and illiquid_share >= 10.0:
        severity = "HIGH" if illiquid_share > 20.0 else "MEDIUM"
        conflicts.append({
            "severity": severity,
            "type": "LIQUIDITY_MISMATCH",
            "message": (
                f"Liquidity need is High, but {illiquid_share:.1f}% of the portfolio is tagged Low liquidity. "
                "This may conflict with near-term cash requirements."
            ),
        })
    if tolerance == "low" and impact_pct < -15.0:
        conflicts.append({
            "severity": "HIGH",
            "type": "RISK_TOLERANCE_BREACH",
            "message": (
                f"The modeled scenario impact is {impact_pct:.1f}%, exceeding a conservative risk profile's "
                "15% stress-loss review threshold. This is a hypothetical scenario, not a forecast."
            ),
        })
    if max_sector_weight > 50.0:
        conflicts.append({
            "severity": "MEDIUM",
            "type": "ASSET_CLASS_CLUSTERING",
            "message": (
                f"The largest sector represents {max_sector_weight:.1f}% of the portfolio, creating "
                "concentration risk under sector-specific disruptions."
            ),
        })

    matrix_info = quant_results.get("correlation_matrix", {}) if isinstance(quant_results, dict) else {}
    high_corr_warning = matrix_info.get("high_correlation_warning") if isinstance(matrix_info, dict) else None
    if high_corr_warning:
        conflicts.append({
            "severity": "MEDIUM",
            "type": "CORRELATED_HOLDINGS",
            "message": str(high_corr_warning),
        })
    return conflicts


def generate_ai_insights(
    portfolio: dict[str, Any],
    quant_results: dict[str, Any],
    custom_prompt: str = "",
) -> dict[str, Any]:
    """Return deterministic scenario parsing, assumptions, conflicts and trade-offs.

    The function name is retained for compatibility with CONTRACT.md. This
    implementation uses deterministic rules and does not call an external LLM.
    """
    if not isinstance(portfolio, dict):
        raise ValueError("portfolio must be an object")
    if not isinstance(quant_results, dict):
        raise ValueError("quant_results must be an object")

    parsed_shocks = parse_custom_scenario(custom_prompt)
    quant_assumptions = quant_results.get("assumptions_used", [])
    if not isinstance(quant_assumptions, list):
        quant_assumptions = []
    assumptions = [str(item) for item in quant_assumptions]
    assumptions.append(
        "Goal conflicts are detected with deterministic rules; they are review prompts, not personalized financial advice."
    )
    assumptions.append(
        "Custom scenario parsing is heuristic. Verify parsed shocks before relying on scenario output."
    )
    if custom_prompt.strip():
        assumptions.append("The custom prompt was parsed locally; no external AI service was called.")

    alternative = quant_results.get("alternative_portfolio", {})
    alternative = alternative if isinstance(alternative, dict) else {}
    tradeoff = str(alternative.get("tradeoff_explanation") or (
        "No alternative allocation comparison was supplied by the quant engine."
    ))
    drawdown_saved = alternative.get("drawdown_saved_inr")
    if drawdown_saved is not None:
        tradeoff += f" Modeled stressed-value difference: ₹{_num(drawdown_saved):,.0f}."

    conflicts = _goal_conflicts(portfolio, quant_results)
    return {
        "parsed_shocks": parsed_shocks,
        "assumptions_list": assumptions,
        "assumptions_used": assumptions,
        "goal_conflicts": conflicts,
        "tradeoff_summary": tradeoff,
        "disclaimer": (
            "This output is educational scenario analysis based on assumptions. It is not a guarantee, "
            "a forecast, or individualized investment advice."
        ),
    }
