export interface RiskAsset {
  ticker: string;
  name: string;
  sector: string;
  amount_inr: number;
}

export interface ScenarioRiskAsset extends RiskAsset {
  asset_class: string;
  liquidity_tag: string;
  currency_exposure: string;
}

export interface InvestorProfileRequest {
  horizon_years: number;
  risk_tolerance: string;
  liquidity_need: string;
  target_goal_inr: number;
}

export interface ScenarioRiskRequest {
  investor_profile: InvestorProfileRequest;
  assets: ScenarioRiskAsset[];
  scenario: {
    preset_name: string;
    market_decline_pct: number;
    interest_rate_change_bps: number;
    sector_shocks: Record<string, number>;
    currency_inr_usd_shift_pct: number;
    custom_ai_prompt: string;
  };
}

export interface ScenarioRiskResponse {
  summary: {
    total_value_inr: number;
    stressed_value_median_inr: number;
    estimated_impact_inr: number;
    estimated_impact_pct: number;
    annualized_volatility_pct: number;
    max_drawdown_pct: number;
    diversification_score_out_of_100: number;
    "illiquid_ share_pct": number;
  };
  composition: {
    by_sector: Array<{ sector: string; weight_pct: number }>;
    by_liquidity: Record<string, number>;
  };
  correlation_matrix: {
    tickers: string[];
    matrix: number[][];
    high_correlation_warning: string;
  };
  chart_data: {
    disclaimer: string;
    historical_observations: Array<{ month: string; actual_value: number }>;
    hypothetical_projection_cone: Array<{
      month: string;
      p10_worst_case: number;
      p50_median_case: number;
      p90_best_case: number;
      rebalanced_p50: number;
    }>;
  };
  ai_analysis: {
    assumptions_used: string[];
    goal_conflicts: Array<{ severity: string; type: string; message: string }>;
    alternative_portfolio: {
      name: string;
      proposed_assets: Array<{
        ticker: string;
        sector: string;
        weight_pct: number;
        amount_inr: number;
      }>;
      stressed_value_median_inr: number;
      drawdown_saved_inr: number;
      tradeoff_explanation: string;
    };
  };
}

export interface ReverseStressTestRequest {
  target_loss_pct: number;
  assets: RiskAsset[];
}

export interface ReverseStressTestResponse {
  target_loss_pct: number;
  portfolio_volatility_pct: number;
  mahalanobis_distance_sigmas: number;
  failure_probability_estimate: number;
  failure_frequency_description: string;
  fragility_ranking: Array<{
    ticker: string;
    name: string;
    sector: string;
    weight_pct: number;
    beta_to_portfolio: number;
    required_shock_pct: number;
    value_loss_inr: number;
    marginal_risk_contribution_pct: number;
    fragility_rank: number;
  }>;
  most_probable_failure_scenario: Record<string, number>;
  summary_narrative: string;
}

export interface ContagionStage {
  stage_number: number;
  stage_name: string;
  title?: string;
  description?: string;
  summary?: string;
  nodes?: Array<{
    id: string;
    label: string;
    description: string;
    calculated_impact_pct: number;
    relationship_to_shock?: string;
    caused_by?: string;
    sensitivity_beta: number;
    rationale: string;
    confidence: string;
  }>;
  affected_holdings?: Array<{
    ticker: string;
    name: string;
    sector: string;
    amount_inr: number;
    weight_pct: number;
    estimated_return_pct: number;
    portfolio_impact_inr: number;
    transmission_pathway: string;
    is_hedging: boolean;
  }>;
  inoculation_strategy?: {
    is_hedging_needed: boolean;
    hedge_instrument: string;
    reallocation_amount_inr: number;
    original_drawdown_inr: number;
    post_hedge_drawdown_inr: number;
    drawdown_saved_inr: number;
    post_hedge_impact_pct: number;
    opportunity_cost: string;
    proposed_rebalance: Array<{
      ticker: string;
      name: string;
      action: "TRIM" | "ALLOCATE";
      amount_change_inr: number;
      reason: string;
    }>;
  };
}

export interface ContagionSimulationRequest {
  scenario_id: string;
  custom_magnitude_pct: number;
  portfolio: { assets: RiskAsset[] };
}

export interface ContagionSimulationResponse {
  scenario: {
    id: string;
    title: string;
    headline: string;
    active_shock_magnitude: number;
  };
  stages: ContagionStage[];
  summary: {
    initial_value: number;
    stressed_value: number;
    net_impact_inr: number;
    net_impact_pct: number;
    largest_drag: string;
    largest_buffer: string;
    drawdown_saved_with_hedge_inr: number;
  };
  is_false_diversification_detected?: boolean;
  nominal_diversification_score?: number;
  effective_tail_diversification_score?: number;
  diversification_haircut_points?: number;
  upstream_dependency?: string;
}
