import type {
  ContagionSimulationRequest,
  ContagionSimulationResponse,
  ReverseStressTestRequest,
  ReverseStressTestResponse,
  ScenarioRiskRequest,
  ScenarioRiskResponse,
} from "../types/riskEngine";

export type {
  ContagionSimulationRequest,
  ContagionSimulationResponse,
  ReverseStressTestRequest,
  ReverseStressTestResponse,
  ScenarioRiskRequest,
  ScenarioRiskResponse,
};

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/+$/, "");

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

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (error) {
    const detail = error instanceof Error ? ` ${error.message}` : "";
    throw new Error(`Cannot reach the risk engine at ${API_BASE_URL}.${detail}`);
  }

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

function postJson<TRequest, TResponse>(
  path: string,
  payload: TRequest,
): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function analyzeScenario(
  payload: ScenarioRiskRequest,
): Promise<ScenarioRiskResponse> {
  return postJson<ScenarioRiskRequest, ScenarioRiskResponse>(
    "/api/analyze-scenario",
    payload,
  );
}

export function runReverseStressTest(
  payload: ReverseStressTestRequest,
): Promise<ReverseStressTestResponse> {
  return postJson<ReverseStressTestRequest, ReverseStressTestResponse>(
    "/api/reverse-stress-test",
    payload,
  );
}

export function simulateContagion(
  payload: ContagionSimulationRequest,
): Promise<ContagionSimulationResponse> {
  return postJson<ContagionSimulationRequest, ContagionSimulationResponse>(
    "/api/contagion/simulate",
    payload,
  );
}
