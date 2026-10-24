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
)
from .ai_agent import (
    generate_ai_insights,
    parse_custom_scenario,
)

__all__ = [
    "run_portfolio_scenario",
    "compute_composition",
    "compute_diversification_score",
    "build_correlation_matrix",
    "compute_stochastic_cone_and_history",
    "generate_alternative_rebalance",
    "generate_ai_insights",
    "parse_custom_scenario",
]
