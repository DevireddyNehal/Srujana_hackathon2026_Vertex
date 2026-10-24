"""
Engine package for Srujana Hackathon 2026 - Portfolio Risk and Scenario Analysis.
Sandbox: Lead (Quant + AI Engine)
"""

from .quant import (
    run_portfolio_scenario,
    compute_composition,
    compute_diversification_score,
    build_correlation_matrix,
    compute_stochastic_cone_and_history,
    generate_alternative_rebalance,
    compute_reverse_stress_test,
    compute_tail_dependence_matrix,
    detect_false_diversification,
    historical_cvar,
    compute_pain_index,
    compute_ulcer_index,
)
from .ai_agent import (
    generate_ai_insights,
    parse_custom_scenario,
)
from .contagion import (
    EconomicDependencyGraph,
    build_economic_dependency_graph,
    get_available_contagion_scenarios,
    simulate_butterfly_shock,
    detect_false_diversification_trap,
)

__all__ = [
    "run_portfolio_scenario",
    "compute_composition",
    "compute_diversification_score",
    "build_correlation_matrix",
    "compute_stochastic_cone_and_history",
    "generate_alternative_rebalance",
    "compute_reverse_stress_test",
    "compute_tail_dependence_matrix",
    "detect_false_diversification",
    "historical_cvar",
    "compute_pain_index",
    "compute_ulcer_index",
    "generate_ai_insights",
    "parse_custom_scenario",
    "EconomicDependencyGraph",
    "build_economic_dependency_graph",
    "get_available_contagion_scenarios",
    "simulate_butterfly_shock",
    "detect_false_diversification_trap",
]

