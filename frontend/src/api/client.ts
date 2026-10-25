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
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => {
    timeoutController.abort(new Error("Request timed out after 15 seconds"));
  }, 15000);

  try {
    const signal = init?.signal ?? timeoutController.signal;
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal });
  } catch (error) {
    const detail = error instanceof Error ? ` ${error.message}` : "";
    throw new Error(`Cannot reach the risk engine at ${API_BASE_URL}.${detail}`);
  } finally {
    clearTimeout(timeoutId);
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

// ==========================================
// TRADING JOURNAL, USER STATS & AUTH API
// ==========================================
import type {
  UserProfile,
  TradeRecord,
  PaginatedTrades,
  PerformanceMetrics,
  DailyPnLPoint,
  BreakdownItem,
} from "../types/trading";

function getAuthHeaders(userId?: string, token?: string): Record<string, string> {
  const headers: Record<string, string> = {};
  const activeUser = userId || (typeof localStorage !== "undefined" ? localStorage.getItem("vertex_active_user_id") : null);
  const activeToken = token || (typeof localStorage !== "undefined" ? localStorage.getItem("vertex_auth_token") : null);
  if (activeUser) headers["X-User-Id"] = activeUser;
  if (activeToken) headers["Authorization"] = `Bearer ${activeToken}`;
  return headers;
}

export async function getDemoUsers(): Promise<UserProfile[]> {
  return requestJson<UserProfile[]>("/api/v1/auth/demo-users");
}

export async function switchDemoUser(userId: string): Promise<{
  status: string;
  active_user_id: string;
  user_name: string;
  token: string;
  message: string;
}> {
  return requestJson<{
    status: string;
    active_user_id: string;
    user_name: string;
    token: string;
    message: string;
  }>(`/api/v1/auth/switch-demo/${userId}`, { method: "POST" });
}

export async function loginUser(credentials: { email: string; password: string }): Promise<{
  status: string;
  user: UserProfile;
  token: string;
  message: string;
}> {
  return requestJson<{
    status: string;
    user: UserProfile;
    token: string;
    message: string;
  }>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
}

export async function registerUser(payload: {
  name: string;
  email: string;
  password: string;
  starting_balance?: number;
  currency?: string;
  timezone?: string;
}): Promise<{
  status: string;
  user: UserProfile;
  token: string;
  message: string;
}> {
  return requestJson<{
    status: string;
    user: UserProfile;
    token: string;
    message: string;
  }>("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getCurrentUserProfile(userId?: string, token?: string): Promise<UserProfile> {
  return requestJson<UserProfile>("/api/v1/auth/me", {
    headers: getAuthHeaders(userId, token),
  });
}

export async function getJournalTrades(params: {
  page?: number;
  page_size?: number;
  symbol?: string;
  direction?: string;
  status?: string;
  outcome?: string;
  strategy?: string;
  session?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
  date_from?: string;
  date_to?: string;
}, userId?: string, token?: string): Promise<PaginatedTrades> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.append(key, String(value));
    }
  }
  return requestJson<PaginatedTrades>(`/api/v1/trades?${query.toString()}`, {
    headers: getAuthHeaders(userId, token),
  });
}

export async function createJournalTrade(trade: Partial<TradeRecord>, userId?: string, token?: string): Promise<TradeRecord> {
  return requestJson<TradeRecord>("/api/v1/trades", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(userId, token),
    },
    body: JSON.stringify(trade),
  });
}

export async function updateJournalTrade(tradeId: string, updates: Partial<TradeRecord>, userId?: string, token?: string): Promise<TradeRecord> {
  return requestJson<TradeRecord>(`/api/v1/trades/${tradeId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(userId, token),
    },
    body: JSON.stringify(updates),
  });
}

export async function deleteJournalTrade(tradeId: string, userId?: string, token?: string): Promise<{ status: string; message: string }> {
  return requestJson<{ status: string; message: string }>(`/api/v1/trades/${tradeId}`, {
    method: "DELETE",
    headers: getAuthHeaders(userId, token),
  });
}

export async function getAnalyticsOverview(rangePreset: string = "all", userId?: string, token?: string, filters?: {
  symbol?: string;
  strategy?: string;
  session?: string;
  direction?: string;
}): Promise<PerformanceMetrics> {
  const query = new URLSearchParams({ range_preset: rangePreset });
  if (filters?.symbol) query.append("symbol", filters.symbol);
  if (filters?.strategy) query.append("strategy", filters.strategy);
  if (filters?.session) query.append("session", filters.session);
  if (filters?.direction) query.append("direction", filters.direction);
  return requestJson<PerformanceMetrics>(`/api/v1/analytics/overview?${query.toString()}`, {
    headers: getAuthHeaders(userId, token),
  });
}

export async function getDailyPnL(rangePreset: string = "30d", userId?: string, token?: string): Promise<DailyPnLPoint[]> {
  return requestJson<DailyPnLPoint[]>(`/api/v1/analytics/daily-pnl?range_preset=${rangePreset}`, {
    headers: getAuthHeaders(userId, token),
  });
}

export async function getBreakdown(
  dimension: "overall" | "session" | "strategy" | "symbol" | "direction" = "overall",
  rangePreset: string = "all",
  userId?: string,
  token?: string
): Promise<BreakdownItem[]> {
  const query = new URLSearchParams({
    group_by: dimension,
    dimension: dimension,
    range_preset: rangePreset,
  });
  return requestJson<BreakdownItem[]>(`/api/v1/analytics/breakdown?${query.toString()}`, {
    headers: getAuthHeaders(userId, token),
  });
}

export async function getTradeReview(
  tradeId: string,
  userId?: string,
  token?: string,
): Promise<{
  status: string;
  trade_id: string;
  symbol: string;
  direction: string;
  net_pnl: number;
  observations: string[];
  suggestions: string[];
  disclaimer: string;
}> {
  return requestJson(`/api/v1/trades/${tradeId}/review`, {
    method: "POST",
    headers: getAuthHeaders(userId, token),
  });
}

export async function importJournalTradesCsv(
  file: File,
  userId?: string,
  token?: string,
): Promise<{
  status: string;
  imported_count: number;
  error_count: number;
  errors?: string[];
}> {
  const formData = new FormData();
  formData.append("file", file);

  const authHeaders = getAuthHeaders(userId, token);
  const response = await fetch(`${API_BASE_URL}/api/v1/trades/import/csv`, {
    method: "POST",
    headers: {
      ...authHeaders,
    },
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Import failed (${response.status}): ${text}`);
  }

  return response.json();
}

export interface NewsArticle {
  id: string;
  headline: string;
  summary: string;
  source: string;
  publishedAt: string;
  url?: string;
  relatedAssets?: string[];
  sentiment?: "bullish" | "bearish" | "neutral";
  impactEstimate?: string;
  category?: string;
  suggestedScenarioId?: "crash" | "rates" | "technology" | "fx" | "custom";
  isLive?: boolean;
}

export async function getMarketNews(
  query?: string,
  asset?: string,
  limit?: number,
): Promise<NewsArticle[]> {
  const params = new URLSearchParams();
  if (query) params.append("query", query);
  if (asset && asset !== "ALL") params.append("asset", asset);
  if (limit) params.append("limit", limit.toString());
  const queryString = params.toString() ? `?${params.toString()}` : "";
  return requestJson<NewsArticle[]>(`/api/v1/market/news${queryString}`);
}



