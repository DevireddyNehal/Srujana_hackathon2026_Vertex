"""
Unit and Integration Tests for Srujana Hackathon 2026 Engine
Validates:
- quant.run_portfolio_scenario
- quant.compute_transmission_spillover
- ai_agent.generate_ai_insights
- ai_agent.diagnose_financial_trilemma
- ai_agent.parse_custom_scenario
- Strict adherence to CONTRACT.md schemas
"""

import sys
from pathlib import Path

# Add backend directory to sys.path so engine can be imported directly
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engine.quant import (
    run_portfolio_scenario,
    compute_composition,
    compute_diversification_score,
    build_correlation_matrix,
    compute_stochastic_cone_and_history,
    compute_transmission_spillover,
)
from engine.ai_agent import (
    generate_ai_insights,
    parse_custom_scenario,
    diagnose_financial_trilemma,
)


def sample_portfolio():
    return {
        "investor_profile": {
            "horizon_years": 1,
            "risk_tolerance": "Low",
            "liquidity_need": "High",
            "target_goal_inr": 1200000,
        },
        "assets": [
            {
                "ticker": "TCS.NS",
                "name": "Tata Consultancy Services",
                "sector": "IT",
                "asset_class": "Equity",
                "amount_inr": 400000,
                "liquidity_tag": "High",
                "currency_exposure": "USD_INR",
            },
            {
                "ticker": "INFY.NS",
                "name": "Infosys Ltd",
                "sector": "IT",
                "asset_class": "Equity",
                "amount_inr": 350000,
                "liquidity_tag": "High",
                "currency_exposure": "USD_INR",
            },
            {
                "ticker": "HDFCBANK.NS",
                "name": "HDFC Bank",
                "sector": "Banking",
                "asset_class": "Equity",
                "amount_inr": 150000,
                "liquidity_tag": "High",
                "currency_exposure": "INR",
            },
            {
                "ticker": "REALTY_LOCKED",
                "name": "Commercial REIT / Locked Debt",
                "sector": "Real Estate",
                "asset_class": "Debt",
                "amount_inr": 100000,
                "liquidity_tag": "Low",
                "currency_exposure": "INR",
            },
        ],
    }


def sample_shocks():
    return {
        "preset_name": "IT Sector Disruption + RBI Rate Hike",
        "market_decline_pct": -15.0,
        "interest_rate_change_bps": 75,
        "sector_shocks": {
            "IT": -25.0,
            "Banking": -10.0,
            "Gold": 8.0,
        },
        "currency_inr_usd_shift_pct": -5.0,
        "custom_ai_prompt": "What if US tech spending freezes and RBI raises repo rate by 75 bps?",
    }


def test_quant_engine_structure_and_types():
    portfolio = sample_portfolio()
    shocks = sample_shocks()

    res = run_portfolio_scenario(portfolio, shocks)

    # 1. Verify top-level keys
    assert "summary" in res
    assert "composition" in res
    assert "correlation_matrix" in res
    assert "chart_data" in res
    assert "alternative_portfolio" in res

    # 2. Verify summary numbers
    summary = res["summary"]
    assert summary["total_value_inr"] == 1000000
    assert summary["stressed_value_median_inr"] < 1000000
    assert summary["estimated_impact_inr"] < 0
    assert summary["estimated_impact_pct"] < 0
    assert summary["diversification_score_out_of_100"] > 0
    assert "illiquid_ share_pct" in summary
    assert "illiquid_share_pct" in summary
    assert summary["illiquid_share_pct"] == 10.0

    # 3. Verify composition
    comp = res["composition"]
    assert len(comp["by_sector"]) > 0
    assert comp["by_sector"][0]["sector"] == "IT"
    assert comp["by_sector"][0]["weight_pct"] == 75.0
    assert comp["by_liquidity"]["High"] == 90.0
    assert comp["by_liquidity"]["Low"] == 10.0

    # 4. Verify correlation matrix
    corr = res["correlation_matrix"]
    assert len(corr["tickers"]) == 4
    assert len(corr["matrix"]) == 4
    assert corr["matrix"][0][0] == 1.0
    assert corr["matrix"][0][1] == 0.88
    assert "TCS.NS and INFY.NS have a 0.88 correlation" in corr["high_correlation_warning"]

    # 5. Verify chart data
    chart = res["chart_data"]
    assert len(chart["historical_observations"]) == 12
    assert chart["historical_observations"][-1]["actual_value"] == 1000000
    assert len(chart["hypothetical_projection_cone"]) == 6
    p1 = chart["hypothetical_projection_cone"][0]
    assert p1["p10_worst_case"] <= p1["p50_median_case"] <= p1["p90_best_case"]
    assert "disclaimer" in chart


def test_factor_transmission_spillover():
    asset_it = {"sector": "IT", "liquidity_tag": "High"}
    asset_locked = {"sector": "Real Estate", "liquidity_tag": "Low"}

    # Test rate hike spillover on IT growth multiple
    spill_it, notes_it = compute_transmission_spillover(asset_it, mkt_decline=0.0, rate_bps=100, fx_shift=0.0)
    assert spill_it < 0.0
    assert any("DCF discount" in n for n in notes_it)

    # Test systemic liquidity freeze on locked asset
    spill_locked, notes_locked = compute_transmission_spillover(asset_locked, mkt_decline=-20.0, rate_bps=0, fx_shift=0.0)
    assert spill_locked < 0.0
    assert any("liquidity freeze" in n for n in notes_locked)


def test_ai_agent_insights_and_trilemma():
    portfolio = sample_portfolio()
    shocks = sample_shocks()
    quant_res = run_portfolio_scenario(portfolio, shocks)

    insights = generate_ai_insights(portfolio, quant_res, shocks["custom_ai_prompt"])

    assert "assumptions_used" in insights
    assert len(insights["assumptions_used"]) >= 4

    # Verify transmission channel notes are surfaced in assumptions
    assert any("Transmission Channel:" in a for a in insights["assumptions_used"])

    assert "goal_conflicts" in insights
    conflict_types = [c["type"] for c in insights["goal_conflicts"]]

    # Verify detection of Financial Trilemma breach (demanding ₹12L from ₹10L in 1 yr with Low risk)
    assert "FINANCIAL_TRILEMMA_BREACH" in conflict_types

    # Verify detection of 1-yr horizon vs 75% equity conflict
    assert "HORIZON_VS_VOLATILITY" in conflict_types

    # Verify detection of Liquidity Cascade risk
    assert "LIQUIDITY_MISMATCH" in conflict_types

    # Verify alternative portfolio details & opportunity cost
    alt = insights["alternative_portfolio"]
    assert alt["name"] == "AI Risk-Adjusted Hedge Allocation"
    assert len(alt["proposed_assets"]) == 4
    assert alt["drawdown_saved_inr"] > 0
    assert "opportunity cost" in alt["tradeoff_explanation"].lower()


def test_custom_scenario_parser():
    parsed = parse_custom_scenario("What if tech crashes by 30% and RBI hikes repo rate by 100 bps?")
    assert parsed["sector_shocks"]["IT"] == -25.0 or parsed["sector_shocks"].get("IT") < 0
    assert parsed["interest_rate_change_bps"] == 100
    assert parsed["market_decline_pct"] < 0


def test_edge_case_empty_portfolio():
    res = run_portfolio_scenario({"assets": []}, {})
    assert res["summary"]["total_value_inr"] == 1000000
    assert res["summary"]["diversification_score_out_of_100"] == 0


def test_defensive_null_inputs():
    # Verify that passing None doesn't crash the engine
    res = run_portfolio_scenario(None, None)
    assert "summary" in res
    assert res["summary"]["total_value_inr"] == 1000000

    insights = generate_ai_insights(None, None)
    assert "assumptions_used" in insights
    assert "goal_conflicts" in insights

