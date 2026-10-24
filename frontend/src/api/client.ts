const API_BASE_URL = "http://localhost:8000";

export interface InvestorProfile {
  horizon_years: number;
  risk_tolerance: string;
  liquidity_need: string;
  target_goal_inr: number;
}

export interface PortfolioAsset {
  ticker: string;
  name: string;
  sector: string;
  asset_class: string;
  amount_inr: number;
  liquidity_tag: string;
  currency_exposure: string;
}

export interface Portfolio {
  id: string;
  name: string;
  investor_profile: InvestorProfile;
  assets: PortfolioAsset[];
}

export interface Scenario {
  preset_name: string;
  market_decline_pct: number;
  interest_rate_change_bps: number;
  sector_shocks: Record<string, number>;
  currency_inr_usd_shift_pct: number;
  custom_ai_prompt: string;
}

export interface ScenarioAnalysisRequest {
  investor_profile: InvestorProfile;
  assets: PortfolioAsset[];
  scenario: Scenario;
}

export interface ScenarioAnalysisResponse {
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
    historical_observations: Array<{
      month: string;
      actual_value: number;
    }>;
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
    goal_conflicts: Array<{
      severity: string;
      type: string;
      message: string;
    }>;
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

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    const details = await response.text();
    throw new Error(
      `API request failed (${response.status} ${response.statusText})${
        details ? `: ${details}` : ""
      }`,
    );
  }

  return response.json() as Promise<T>;
}

export async function getPortfolios(): Promise<{ portfolios: Portfolio[] }> {
  return requestJson<{ portfolios: Portfolio[] }>("/api/portfolios");
}

export async function analyzeScenario(
  payload: ScenarioAnalysisRequest,
): Promise<ScenarioAnalysisResponse> {
  return requestJson<ScenarioAnalysisResponse>("/api/analyze-scenario", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
