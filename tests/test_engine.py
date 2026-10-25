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

import math
import sys
from pathlib import Path
import pytest

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
    compute_reverse_stress_test,
    compute_tail_dependence_matrix,
    detect_false_diversification,
    historical_cvar,
    compute_pain_index,
    compute_ulcer_index,
)
from engine.ai_agent import (
    generate_ai_insights,
    parse_custom_scenario,
    diagnose_financial_trilemma,
)
from engine.contagion import (
    EconomicDependencyGraph,
    build_economic_dependency_graph,
    get_available_contagion_scenarios,
    simulate_butterfly_shock,
    detect_false_diversification_trap,
    _compute_contagion_inoculation,
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


def test_economic_dependency_graph():
    graph = build_economic_dependency_graph()
    assert len(graph.nodes) > 10
    
    # Check oil shock node and successors
    assert "shock_oil" in graph.nodes
    oil_succs = graph.get_successors("shock_oil")
    assert len(oil_succs) >= 2
    
    # Check edge properties
    edge = oil_succs[0]
    assert "target" in edge
    assert "sensitivity" in edge
    assert "rationale" in edge
    assert "confidence" in edge
    
    # Check dictionary serialization for frontend renderers
    d = graph.to_dict()
    assert "nodes" in d
    assert "edges" in d
    assert len(d["nodes"]) == len(graph.nodes)


def test_butterfly_effect_simulation_stages():
    portfolio = sample_portfolio()
    sim = simulate_butterfly_shock("oil_supply_disruption", portfolio)
    
    assert "stages" in sim
    stages = sim["stages"]
    assert len(stages) == 4
    
    # Stage 0: Initial Shock
    s0 = stages[0]
    assert s0["stage_number"] == 0
    assert "Initial Shock" in s0["stage_name"]
    assert "Oil" in s0["title"]
    assert "assumptions" in s0
    
    # Stage 1: First-Order Effects
    s1 = stages[1]
    assert s1["stage_number"] == 1
    assert len(s1["nodes"]) > 0
    assert all("sensitivity" in n and "rationale" in n for n in s1["nodes"])
    
    # Stage 2: Second-Order Effects
    s2 = stages[2]
    assert s2["stage_number"] == 2
    assert len(s2["nodes"]) > 0
    assert all("caused_by" in n and "sensitivity" in n for n in s2["nodes"])
    
    # Stage 3: Portfolio Exposure & Single-Counted Impact
    s3 = stages[3]
    assert s3["stage_number"] == 3
    assert s3["initial_portfolio_value_inr"] == 1000000
    assert "affected_holdings" in s3
    assert len(s3["affected_holdings"]) == 4
    
    # Verify exact summation of holding rupee impacts (zero double-counting)
    computed_sum = sum(h["portfolio_impact_inr"] for h in s3["affected_holdings"])
    assert s3["estimated_impact_inr"] == computed_sum
    assert s3["stressed_portfolio_value_inr"] == s3["initial_portfolio_value_inr"] + computed_sum
    assert "formula_used" in s3
    assert "R_p = sum(w_i * r_i)" in s3["formula_used"]


def test_butterfly_effect_available_scenarios():
    scenarios = get_available_contagion_scenarios()
    assert len(scenarios) >= 3
    ids = [s["id"] for s in scenarios]
    assert "oil_supply_disruption" in ids
    assert "rbi_repo_tightening" in ids
    assert "us_tech_spending_freeze" in ids


def test_api_contagion_endpoints():
    pytest.importorskip("main")
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    # 1. GET /api/contagion/scenarios
    resp = client.get("/api/contagion/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) == 3

    # 2. POST /api/contagion/simulate
    resp2 = client.post("/api/contagion/simulate", json={"scenario_id": "oil_supply_disruption"})
    assert resp2.status_code == 200
    res_data = resp2.json()
    assert "stages" in res_data
    assert len(res_data["stages"]) == 4
    assert "summary" in res_data
    assert "net_impact_inr" in res_data["summary"]


def test_reverse_stress_testing_mpfs():
    portfolio = sample_portfolio()
    rst = compute_reverse_stress_test(portfolio, target_loss_pct=15.0)

    # 1. Verification of mathematical structure
    assert rst["target_loss_pct"] == 15.0
    assert rst["portfolio_volatility_pct"] > 0.0
    assert rst["mahalanobis_distance_sigmas"] > 0.0
    assert "fragility_ranking" in rst
    assert len(rst["fragility_ranking"]) == 4

    # 2. Check Mahalanobis Distance: D_M = L / sigma_p
    expected_dm = round(15.0 / rst["portfolio_volatility_pct"], 2)
    assert abs(rst["mahalanobis_distance_sigmas"] - expected_dm) <= 0.02

    # 3. Check exact failure condition: sum(w_i * S*_i) == -L
    assets = portfolio["assets"]
    total_val = sum(a["amount_inr"] for a in assets)
    shocks = rst["most_probable_failure_scenario"]
    weighted_loss = sum((a["amount_inr"] / total_val) * shocks[a["ticker"]] for a in assets)
    assert abs(weighted_loss - (-15.0)) < 0.05

    # 4. Fragility ranking verification (sorted by beta descending)
    ranks = rst["fragility_ranking"]
    for i in range(len(ranks) - 1):
        assert ranks[i]["beta_to_portfolio"] >= ranks[i + 1]["beta_to_portfolio"]
        assert ranks[i]["fragility_rank"] == i + 1

    # Marginal risk contributions sum to approximately 100%
    sum_marginal = sum(r["marginal_risk_contribution_pct"] for r in ranks)
    assert abs(sum_marginal - 100.0) < 0.5

    # 5. Single asset portfolio edge case
    single_p = {"assets": [{"ticker": "NIFTY50", "sector": "IT", "amount_inr": 500000}]}
    single_rst = compute_reverse_stress_test(single_p, target_loss_pct=20.0)
    assert single_rst["target_loss_pct"] == 20.0
    assert single_rst["fragility_ranking"][0]["beta_to_portfolio"] == 1.0
    assert single_rst["most_probable_failure_scenario"]["NIFTY50"] == -20.0

    # 6. Empty portfolio edge case
    empty_rst = compute_reverse_stress_test({"assets": []}, target_loss_pct=10.0)
    assert empty_rst["target_loss_pct"] == 10.0
    assert len(empty_rst["fragility_ranking"]) == 0


def test_clayton_copula_lower_tail_dependence():
    assets = sample_portfolio()["assets"]
    corr_info = build_correlation_matrix(assets)
    tail_info = compute_tail_dependence_matrix(corr_info)

    assert "tail_dependence_matrix" in tail_info
    mat = tail_info["tail_dependence_matrix"]
    n = len(mat)
    assert n == 4

    # 1. Diagonal elements must be 1.0
    for i in range(n):
        assert mat[i][i] == 1.0

    # 2. Symmetry: lambda_L(i, j) == lambda_L(j, i)
    for i in range(n):
        for j in range(n):
            assert mat[i][j] == mat[j][i]

    # 3. High tail dependence between TCS and INFY (rho = 0.88)
    tcs_idx = tail_info["tickers"].index("TCS.NS")
    infy_idx = tail_info["tickers"].index("INFY.NS")
    lambda_tcs_infy = mat[tcs_idx][infy_idx]
    assert lambda_tcs_infy >= 0.80

    # 4. Check high_tail_dependence_pairs
    high_pairs = tail_info["high_tail_dependence_pairs"]
    assert len(high_pairs) >= 1
    tcs_pair = next(p for p in high_pairs if "TCS.NS" in (p["asset_1"], p["asset_2"]) and "INFY.NS" in (p["asset_1"], p["asset_2"]))
    assert tcs_pair["severity"] == "CRITICAL"
    assert tcs_pair["lower_tail_dependence"] >= 0.80

    # 5. Non-positive correlation yields zero lower tail dependence
    mock_corr = {
        "tickers": ["EQUITY", "GOLD"],
        "matrix": [[1.0, -0.20], [-0.20, 1.0]]
    }
    tail_neg = compute_tail_dependence_matrix(mock_corr)
    assert tail_neg["tail_dependence_matrix"][0][1] == 0.0


def test_false_diversification_detector():
    # Scenario 1: Upstream Commodity Bottleneck Trap
    # Asian Paints (Paints) + IndiGo (Aviation) + Tata Motors (Auto)
    commodity_portfolio = {
        "assets": [
            {"ticker": "ASIANPAINT.NS", "name": "Asian Paints", "sector": "Paints", "amount_inr": 400000},
            {"ticker": "INDIGO.NS", "name": "InterGlobe Aviation", "sector": "Aviation", "amount_inr": 350000},
            {"ticker": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Automotive", "amount_inr": 250000},
        ]
    }
    result = detect_false_diversification(commodity_portfolio)

    assert result["is_false_diversification_detected"] is True
    assert result["trap_severity"] in ["CRITICAL", "HIGH"]
    assert len(result["traps"]) >= 1

    trap = next(t for t in result["traps"] if t["trap_type"] == "UPSTREAM_COMMODITY_DEPENDENCY")
    assert "Crude Oil" in trap["name"] or "Crude Oil" in trap["common_vulnerability"]
    assert "Asian Paints" in trap["explanation"] or "ASIANPAINT.NS" in trap["affected_assets"]
    assert result["effective_tail_diversification_score"] < result["nominal_diversification_score"]
    assert "remedy_recommendation" in result

    # Also verify contagion module wrapper
    contagion_result = detect_false_diversification_trap(commodity_portfolio)
    assert contagion_result["is_false_diversification_detected"] is True

    # Scenario 2: IT Duplication Trap
    it_portfolio = {
        "assets": [
            {"ticker": "TCS.NS", "name": "TCS", "sector": "IT", "amount_inr": 500000},
            {"ticker": "INFY.NS", "name": "Infosys", "sector": "IT", "amount_inr": 500000},
        ]
    }
    it_result = detect_false_diversification(it_portfolio)
    assert it_result["is_false_diversification_detected"] is True
    assert any(t["trap_type"] == "INTRA_SECTOR_TAIL_CONCENTRATION" for t in it_result["traps"])


def test_institutional_tail_risk_cvar_and_pain_index():
    # 1. Historical CVaR calculation
    returns = [-10.0, -8.0, -6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0]
    # At 90% confidence (10th percentile cutoff), worst loss is -10.0
    cvar_90 = historical_cvar(returns, confidence=0.90)
    assert cvar_90 <= -9.0

    # Edge cases
    assert historical_cvar([], confidence=0.95) == 0.0
    assert historical_cvar([-5.5], confidence=0.95) == -5.5
    assert historical_cvar(None) == 0.0

    # 2. Behavioral Pain Index & Ulcer Index
    flat_curve = [100.0, 105.0, 110.0, 115.0]
    assert compute_pain_index(flat_curve) == 0.0
    assert compute_ulcer_index(flat_curve) == 0.0

    drawdown_curve = [100.0, 90.0, 80.0, 90.0, 100.0]
    pain_idx = compute_pain_index(drawdown_curve)
    ulcer_idx = compute_ulcer_index(drawdown_curve)
    assert pain_idx == 8.0  # mean of (0, 10, 20, 10, 0)
    assert ulcer_idx > 0.0
    assert abs(ulcer_idx - 10.954) < 0.01

    # 3. Quant engine summary integration
    portfolio = sample_portfolio()
    shocks = sample_shocks()
    quant_res = run_portfolio_scenario(portfolio, shocks)

    summary = quant_res["summary"]
    assert "cvar_95_pct" in summary
    assert "pain_index" in summary
    assert "ulcer_index" in summary
    assert isinstance(summary["cvar_95_pct"], float)
    assert isinstance(summary["pain_index"], float)
    assert isinstance(summary["ulcer_index"], float)
    # Check dual export of summary and risk_metrics
    assert "risk_metrics" in quant_res
    assert quant_res["risk_metrics"] == summary
    assert "historical_series" in quant_res
    assert "hypothetical_cone" in quant_res


def test_api_reverse_stress_test_endpoint():
    pytest.importorskip("main")
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    # 1. Default call (loads portfolio from mock-data)
    resp = client.post("/api/reverse-stress-test", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_loss_pct"] == 15.0
    assert data["portfolio_volatility_pct"] > 0
    assert data["mahalanobis_distance_sigmas"] > 0
    assert len(data["fragility_ranking"]) > 0
    assert "most_probable_failure_scenario" in data

    # 2. Custom target loss
    custom_resp = client.post(
        "/api/reverse-stress-test",
        json={"target_loss_pct": 25.0, "portfolio": sample_portfolio()},
    )
    assert custom_resp.status_code == 200
    custom_data = custom_resp.json()
    assert custom_data["target_loss_pct"] == 25.0
    assert len(custom_data["fragility_ranking"]) == 4
    assert custom_data["fragility_ranking"][0]["fragility_rank"] == 1


def test_api_analyze_scenario_endpoint():
    pytest.importorskip("main")
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    payload = {
        "investor_profile": {
            "horizon_years": 1,
            "risk_tolerance": "Low",
            "liquidity_need": "High",
            "target_goal_inr": 1000000,
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
                "ticker": "HDFCBANK.NS",
                "name": "HDFC Bank",
                "sector": "Banking",
                "asset_class": "Equity",
                "amount_inr": 600000,
                "liquidity_tag": "High",
                "currency_exposure": "INR",
            },
        ],
        "scenario": {
            "preset_name": "Test Shock",
            "market_decline_pct": -15.0,
            "interest_rate_change_bps": 50,
            "sector_shocks": {"IT": -20.0},
            "currency_inr_usd_shift_pct": -2.0,
            "custom_ai_prompt": "",
        },
    }

    resp = client.post("/api/analyze-scenario", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "composition" in data
    assert "correlation_matrix" in data
    assert "chart_data" in data
    assert "ai_analysis" in data
    assert data["summary"]["total_value_inr"] == 1000000
    assert "cvar_95_pct" in data["summary"]
    assert "pain_index" in data["summary"]


def test_edge_case_reverse_stress_test_variations():
    import numpy as np

    # 1. Non-positive definite correlation matrix test
    # Matrix with negative eigenvalue
    bad_corr = {
        "tickers": ["A", "B", "C"],
        "matrix": [
            [1.0, 0.90, 0.90],
            [0.90, 1.0, -0.90],
            [0.90, -0.90, 1.0],
        ]
    }
    portfolio = {
        "assets": [
            {"ticker": "A", "sector": "IT", "amount_inr": 300000},
            {"ticker": "B", "sector": "Banking", "amount_inr": 300000},
            {"ticker": "C", "sector": "Energy", "amount_inr": 400000},
        ]
    }
    rst = compute_reverse_stress_test(portfolio, target_loss_pct=15.0, correlation_matrix=bad_corr)
    assert rst["portfolio_volatility_pct"] > 0
    assert rst["mahalanobis_distance_sigmas"] > 0
    assert len(rst["fragility_ranking"]) == 3

    # 2. All weights equal to zero
    zero_p = {
        "assets": [
            {"ticker": "X", "sector": "IT", "amount_inr": 0},
            {"ticker": "Y", "sector": "Banking", "amount_inr": 0},
        ]
    }
    rst_zero = compute_reverse_stress_test(zero_p, target_loss_pct=10.0)
    assert rst_zero["portfolio_volatility_pct"] > 0
    for item in rst_zero["fragility_ranking"]:
        assert item["value_loss_inr"] == 0

    # 3. target_loss_pct = None fallback
    rst_none = compute_reverse_stress_test(portfolio, target_loss_pct=None)
    assert rst_none["target_loss_pct"] == 15.0

    # 4. Bare list portfolio input
    bare_list = [
        {"ticker": "TCS.NS", "sector": "IT", "amount_inr": 500000},
        {"ticker": "HDFCBANK.NS", "sector": "Banking", "amount_inr": 500000},
    ]
    rst_list = compute_reverse_stress_test(bare_list, target_loss_pct=12.0)
    assert len(rst_list["fragility_ranking"]) == 2
    assert rst_list["fragility_ranking"][0]["ticker"] in ["TCS.NS", "HDFCBANK.NS"]

    # 5. Case-insensitive sector resolution
    lower_sec_p = [
        {"ticker": "TCS.NS", "sector": "it", "amount_inr": 500000},
        {"ticker": "HDFCBANK.NS", "sector": "banking", "amount_inr": 500000},
    ]
    rst_lower = compute_reverse_stress_test(lower_sec_p, target_loss_pct=10.0)
    assert rst_lower["portfolio_volatility_pct"] > 0


def test_edge_case_clayton_copula_and_false_diversification():
    # 1. Empty correlation matrix returns all required keys including average_tail_dependence
    empty_res = compute_tail_dependence_matrix({})
    assert "average_tail_dependence" in empty_res
    assert empty_res["average_tail_dependence"] == 0.0

    none_res = compute_tail_dependence_matrix(None)
    assert "average_tail_dependence" in none_res
    assert none_res["average_tail_dependence"] == 0.0

    # 2. String/bad entry resilience in correlation matrix
    bad_mat = {
        "tickers": ["A", "B"],
        "matrix": [[1.0, "invalid_num"], ["invalid_num", 1.0]],
    }
    tail_bad = compute_tail_dependence_matrix(bad_mat)
    assert tail_bad["tail_dependence_matrix"][0][1] == 0.0

    # 3. Bare list input in detect_false_diversification
    bare_paints_aviation = [
        {"ticker": "ASIANPAINT.NS", "name": "Asian Paints", "sector": "Paints", "amount_inr": 500000},
        {"ticker": "INDIGO.NS", "name": "InterGlobe Aviation", "sector": "Aviation", "amount_inr": 500000},
    ]
    res = detect_false_diversification(bare_paints_aviation)
    assert res["is_false_diversification_detected"] is True
    assert any(t["trap_type"] == "UPSTREAM_COMMODITY_DEPENDENCY" for t in res["traps"])

    # 4. Strictly non-negative haircut when nominal diversification is very low
    low_nom_p = {
        "assets": [
            {"ticker": "TCS.NS", "sector": "IT", "amount_inr": 1000000},
        ]
    }
    res_low = detect_false_diversification(low_nom_p)
    assert res_low["diversification_haircut_points"] >= 0
    assert res_low["effective_tail_diversification_score"] <= res_low["nominal_diversification_score"]

    # 5. Intra-sector duplication in Banking
    banking_p = {
        "assets": [
            {"ticker": "HDFCBANK.NS", "sector": "Banking", "amount_inr": 500000},
            {"ticker": "ICICIBANK.NS", "sector": "Banking", "amount_inr": 500000},
        ]
    }
    res_bank = detect_false_diversification(banking_p)
    assert any(t["trap_type"] == "INTRA_SECTOR_TAIL_CONCENTRATION" for t in res_bank["traps"])


def test_edge_case_cvar_pain_nan_inputs():
    # 1. NaN and Inf filtering in historical_cvar
    cvar_nan = historical_cvar([-10.0, float("nan"), -6.0, float("inf"), -4.0], confidence=0.90)
    assert isinstance(cvar_nan, float)
    assert not math.isnan(cvar_nan)
    assert cvar_nan <= -6.0

    # 2. Percentage confidence (e.g. 90.0 instead of 0.90)
    cvar_pct = historical_cvar([-10.0, -8.0, -6.0, -4.0, -2.0, 0.0], confidence=90.0)
    assert cvar_pct <= -8.0

    # 3. NaN filtering in pain and ulcer index
    curve_with_nan = [100.0, float("nan"), 90.0, 80.0, 100.0]
    pain = compute_pain_index(curve_with_nan)
    ulcer = compute_ulcer_index(curve_with_nan)
    assert not math.isnan(pain)
    assert not math.isnan(ulcer)
    assert pain > 0.0
    assert ulcer > 0.0


def test_api_reverse_stress_test_top_level_assets_and_empty():
    pytest.importorskip("main")
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    # 1. Submit top-level assets (should NOT overwrite with mock data)
    resp = client.post("/api/reverse-stress-test", json={
        "assets": [
            {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy", "amount_inr": 600000},
            {"ticker": "TCS.NS", "name": "TCS", "sector": "IT", "amount_inr": 400000},
        ],
        "target_loss_pct": 18.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_loss_pct"] == 18.0
    tickers = [x["ticker"] for x in data["fragility_ranking"]]
    assert "RELIANCE.NS" in tickers
    assert "TCS.NS" in tickers
    assert "HDFCBANK.NS" not in tickers  # Confirm mock portfolio was NOT used

    # 2. Submit bare list portfolio
    resp_list = client.post("/api/reverse-stress-test", json={
        "portfolio": [
            {"ticker": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Auto", "amount_inr": 300000},
        ],
        "target_loss_pct": 10.0,
    })
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert len(data_list["fragility_ranking"]) == 1
    assert data_list["fragility_ranking"][0]["ticker"] == "TATAMOTORS.NS"

    # 3. Submit explicit empty portfolio (should return empty result, NOT mock data)
    resp_empty = client.post("/api/reverse-stress-test", json={"portfolio": {"assets": []}})
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()["fragility_ranking"]) == 0

    # 4. Submit top-level assets to contagion simulate
    resp_contagion = client.post("/api/contagion/simulate", json={
        "scenario_id": "oil_supply_disruption",
        "assets": [
            {"ticker": "INDIGO.NS", "name": "InterGlobe Aviation", "sector": "Aviation", "amount_inr": 500000},
        ],
    })
    assert resp_contagion.status_code == 200
    s3_holdings = resp_contagion.json()["stages"][3]["affected_holdings"]
    assert len(s3_holdings) == 1
    assert s3_holdings[0]["ticker"] == "INDIGO.NS"


def test_contagion_inoculation_resilient_and_top_level_fda():
    # 1. Resilient portfolio (current_loss_inr >= 0)
    resilient_alloc = _compute_contagion_inoculation(
        assets=[],
        affected_holdings=[],
        total_portfolio_value=1_000_000,
        current_loss_inr=5000,
        shock_id="oil_supply_disruption",
    )
    assert resilient_alloc["is_hedging_needed"] is False
    assert resilient_alloc["hedge_instrument"] == "None (Portfolio Resilient)"
    assert resilient_alloc["reallocation_amount_inr"] == 0
    assert resilient_alloc["original_drawdown_inr"] == 0
    assert resilient_alloc["post_hedge_drawdown_inr"] == 0
    assert resilient_alloc["drawdown_saved_inr"] == 0
    assert resilient_alloc["post_hedge_impact_pct"] == 0.5
    assert "positive resilience" in resilient_alloc["opportunity_cost"]
    assert "positive resilience" in resilient_alloc["message"]
    assert resilient_alloc["proposed_rebalance"] == []

    # Edge case: zero portfolio value
    zero_val_alloc = _compute_contagion_inoculation(
        assets=[],
        affected_holdings=[],
        total_portfolio_value=0,
        current_loss_inr=0,
        shock_id="oil_supply_disruption",
    )
    assert zero_val_alloc["post_hedge_impact_pct"] == 0.0

    # Edge case: zero portfolio value with negative loss
    zero_val_loss_alloc = _compute_contagion_inoculation(
        assets=[],
        affected_holdings=[],
        total_portfolio_value=0,
        current_loss_inr=-5000,
        shock_id="oil_supply_disruption",
    )
    assert zero_val_loss_alloc["is_hedging_needed"] is True
    assert zero_val_loss_alloc["post_hedge_impact_pct"] == 0.0

    # 2. Top-level FDA mirroring in contagion API
    pytest.importorskip("main")
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    resp = client.post("/api/contagion/simulate", json={"scenario_id": "oil_supply_disruption"})
    assert resp.status_code == 200
    data = resp.json()
    assert "is_false_diversification_detected" in data
    assert "nominal_diversification_score" in data
    assert "effective_tail_diversification_score" in data
    assert "diversification_haircut_points" in data
    assert "upstream_dependency" in data
    assert data["is_false_diversification_detected"] is True
    assert data["upstream_dependency"] is not None

    # Test portfolio without false diversification trap returns upstream_dependency as None
    resp_no_fda = client.post(
        "/api/contagion/simulate",
        json={
            "scenario_id": "oil_supply_disruption",
            "portfolio": {
                "assets": [
                    {"ticker": "GOLDBEES.NS", "name": "Gold ETF", "sector": "Gold", "amount_inr": 1_000_000}
                ]
            },
        },
    )
    assert resp_no_fda.status_code == 200
    data_no_fda = resp_no_fda.json()
    assert data_no_fda["is_false_diversification_detected"] is False
    assert data_no_fda["upstream_dependency"] is None
    # Resilient portfolio key_takeaway must safely format without IndexError
    assert "No holdings experience negative transmission drag" in data_no_fda["stages"][3]["key_takeaway"]

    # Test portfolio with crude oil upstream dependency
    resp_oil_fda = client.post(
        "/api/contagion/simulate",
        json={
            "scenario_id": "oil_supply_disruption",
            "portfolio": {
                "assets": [
                    {"ticker": "ASIANPAINT.NS", "name": "Asian Paints", "sector": "Paints", "amount_inr": 500_000},
                    {"ticker": "INDIGO.NS", "name": "InterGlobe Aviation", "sector": "Airlines", "amount_inr": 500_000},
                ]
            },
        },
    )
    assert resp_oil_fda.status_code == 200
    data_oil_fda = resp_oil_fda.json()
    assert data_oil_fda["is_false_diversification_detected"] is True
    assert "Crude Oil" in data_oil_fda["upstream_dependency"]



