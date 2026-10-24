# SRUJANA HACKATHON — F-06: Investment Portfolio Risk & Scenario Analysis
**Master Team Contract, Folder Sandbox & API Schema (`CONTRACT.md`)**

> **AGENT INSTRUCTION:** Read this file before creating or modifying any code. Strictly obey the folder locks below and never deviate from the JSON schemas defined in Section 2.

---

## 1. Team Roles & Strict Folder Sandbox (Zero Git Collisions)

| Teammate | Role | Allowed Folders / Files | Strictly Off-Limits |
| :--- | :--- | :--- | :--- |
| **1. Lead (You)** | **Quant + AI Engine & Repo Lead** | `/backend/engine/quant.py`<br>`/backend/engine/ai_agent.py`<br>`/backend/engine/__init__.py` | Do not edit `/frontend` or `/backend/main.py` directly (expose functions for Zama to import). |
| **2. Zama** | **FastAPI Server, DB & Mock Data** | `/backend/main.py`<br>`/backend/database.py`<br>`/mock-data/portfolios.json` | Do not edit `/backend/engine/` or `/frontend`. |
| **3. Ahmad** | **Frontend Lead (App Shell & Pages)** | `/frontend/src/pages/`<br>`/frontend/src/App.tsx`<br>`/frontend/src/api/` | Do not edit `/frontend/src/components/widgets/` or `/backend`. |
| **4. Shyam** | **Visual Widgets + PPT & Video** | `/frontend/src/components/widgets/` | Do not edit `App.tsx`, `/pages/`, or `/backend`. |

---

## 2. Exact Python Interface (You $\leftrightarrow$ Zama)

Zama's `/backend/main.py` will import two master functions from `/backend/engine/`:

```python
# 1. Core Portfolio Risk, Scenario Simulation & AI Conflict Check
from engine.quant import run_portfolio_scenario
from engine.ai_agent import generate_ai_insights, parse_custom_scenario

# Signature 1: Quant Math Engine
def run_portfolio_scenario(portfolio: dict, scenario_shocks: dict) -> dict:
    """
    Inputs: portfolio dict + shock multipliers (e.g., {"market_drop_pct": -15, ...})
    Returns: composition, risk_metrics, correlation_matrix, historical_series,
             hypothetical_cone (p10, p50, p90), and alternative_portfolio.
    """

# Signature 2: AI Scenario Translator & Goal-Conflict Advisor
def generate_ai_insights(portfolio: dict, quant_results: dict, custom_prompt: str = "") -> dict:
    """
    Returns: parsed_shocks, assumptions_list, goal_conflicts, and tradeoff_summary.
    """
```

---

## 3. FastAPI Endpoints & JSON Contract (Zama $\leftrightarrow$ Ahmad & Shyam)

**Base URL:** `http://localhost:8000` (CORS enabled for `*`)

### Endpoint 1: `GET /api/portfolios`
Returns the 3 pre-loaded Indian investor demo portfolios from `/mock-data/portfolios.json`.

**Response JSON:**
```json
{
  "portfolios": [
    {
      "id": "tech-heavy",
      "name": "Aggressive Growth (Hidden IT Concentration)",
      "investor_profile": {
        "horizon_years": 1,
        "risk_tolerance": "Low",
        "liquidity_need": "High",
        "target_goal_inr": 1000000
      },
      "assets": [
        {
          "ticker": "TCS.NS",
          "name": "Tata Consultancy Services",
          "sector": "IT",
          "asset_class": "Equity",
          "amount_inr": 400000,
          "liquidity_tag": "High",
          "currency_exposure": "USD_INR"
        },
        {
          "ticker": "INFY.NS",
          "name": "Infosys Ltd",
          "sector": "IT",
          "asset_class": "Equity",
          "amount_inr": 350000,
          "liquidity_tag": "High",
          "currency_exposure": "USD_INR"
        },
        {
          "ticker": "HDFCBANK.NS",
          "name": "HDFC Bank",
          "sector": "Banking",
          "asset_class": "Equity",
          "amount_inr": 150000,
          "liquidity_tag": "High",
          "currency_exposure": "INR"
        },
        {
          "ticker": "REALTY_LOCKED",
          "name": "Commercial REIT / Locked Debt",
          "sector": "Real Estate",
          "asset_class": "Debt",
          "amount_inr": 100000,
          "liquidity_tag": "Low",
          "currency_exposure": "INR"
        }
      ]
    }
  ]
}
```

---

### Endpoint 2: `POST /api/analyze-scenario`
Analyzes the portfolio, runs the hypothetical stress test, checks investor goal/liquidity conflicts, and returns the side-by-side alternative allocation.

**Request Payload (Sent by Ahmad's Frontend):**
```json
{
  "investor_profile": {
    "horizon_years": 1,
    "risk_tolerance": "Low",
    "liquidity_need": "High",
    "target_goal_inr": 1000000
  },
  "assets": [
    {
      "ticker": "TCS.NS",
      "name": "Tata Consultancy Services",
      "sector": "IT",
      "asset_class": "Equity",
      "amount_inr": 400000,
      "liquidity_tag": "High",
      "currency_exposure": "USD_INR"
    }
  ],
  "scenario": {
    "preset_name": "IT Sector Disruption + RBI Rate Hike",
    "market_decline_pct": -15.0,
    "interest_rate_change_bps": 75,
    "sector_shocks": {
      "IT": -25.0,
      "Banking": -10.0,
      "Gold": 8.0
    },
    "currency_inr_usd_shift_pct": -5.0,
    "custom_ai_prompt": "What if US tech spending freezes and RBI raises repo rate by 75 bps?"
  }
}
```

**Response Payload (Returned by Zama's FastAPI + Your Engine):**
```json
{
  "summary": {
    "total_value_inr": 1000000,
    "stressed_value_median_inr": 795000,
    "estimated_impact_inr": -205000,
    "estimated_impact_pct": -20.5,
    "annualized_volatility_pct": 22.4,
    "max_drawdown_pct": -28.1,
    "diversification_score_out_of_100": 34,
    "illiquid_ share_pct": 10.0
  },
  "composition": {
    "by_sector": [
      { "sector": "IT", "weight_pct": 75.0 },
      { "sector": "Banking", "weight_pct": 15.0 },
      { "sector": "Real Estate", "weight_pct": 10.0 }
    ],
    "by_liquidity": {
      "High": 90.0,
      "Low": 10.0
    }
  },
  "correlation_matrix": {
    "tickers": ["TCS.NS", "INFY.NS", "HDFCBANK.NS"],
    "matrix": [
      [1.0, 0.88, 0.42],
      [0.88, 1.0, 0.39],
      [0.42, 0.39, 1.0]
    ],
    "high_correlation_warning": "TCS.NS and INFY.NS have a 0.88 correlation—owning both provides false diversification against IT/USD shocks."
  },
  "chart_data": {
    "disclaimer": "Historical observations reflect past NSE data. Hypothetical projections show 10th-90th percentile uncertainty ranges and are not guaranteed results.",
    "historical_observations": [
      { "month": "2025-11", "actual_value": 910000 },
      { "month": "2026-05", "actual_value": 965000 },
      { "month": "2026-10", "actual_value": 1000000 }
    ],
    "hypothetical_projection_cone": [
      {
        "month": "2026-11",
        "p10_worst_case": 820000,
        "p50_median_case": 860000,
        "p90_best_case": 910000,
        "rebalanced_p50": 945000
      },
      {
        "month": "2027-04",
        "p10_worst_case": 730000,
        "p50_median_case": 795000,
        "p90_best_case": 880000,
        "rebalanced_p50": 960000
      }
    ]
  },
  "ai_analysis": {
    "assumptions_used": [
      "Applied a -25% shock to IT equities due to simulated US tech freeze.",
      "Applied a +75 bps interest-rate sensitivity discount to rate-sensitive Banking and Real Estate assets.",
      "Monte Carlo bands assume 500 stochastic paths using 3-year historical covariance."
    ],
    "goal_conflicts": [
      {
        "severity": "HIGH",
        "type": "HORIZON_VS_VOLATILITY",
        "message": "Your investment horizon is only 1 year with Low risk tolerance, but 75% of your capital is in high-volatility IT equities."
      },
      {
        "severity": "MEDIUM",
        "type": "LIQUIDITY_MISMATCH",
        "message": "You marked Liquidity Need as High, but ₹1,00,000 (10%) is in locked Real Estate debt."
      }
    ],
    "alternative_portfolio": {
      "name": "AI Risk-Adjusted Hedge Allocation",
      "proposed_assets": [
        { "ticker": "TCS.NS", "sector": "IT", "weight_pct": 25.0, "amount_inr": 250000 },
        { "ticker": "HDFCBANK.NS", "sector": "Banking", "weight_pct": 25.0, "amount_inr": 250000 },
        { "ticker": "GOLDBEES.NS", "sector": "Gold", "weight_pct": 20.0, "amount_inr": 200000 },
        { "ticker": "LIQUIDBEES.NS", "sector": "Liquid Debt", "weight_pct": 30.0, "amount_inr": 300000 }
      ],
      "stressed_value_median_inr": 940000,
      "drawdown_saved_inr": 145000,
      "tradeoff_explanation": "Reduces crash loss under this scenario from -20.5% to -6.0% and satisfies your 1-year High Liquidity goal, at the trade-off of capping bull-market upside by ~3.2% annually."
    }
  }
}
```

---

## 4. Props Contract for Shyam's 3 Isolated Widgets (`/frontend/src/components/widgets/`)

Shyam builds these 3 components accepting standard props so Ahmad can drop them straight into `Dashboard.tsx`:

1. **`<HistoricalVsHypotheticalChart data={response.chart_data} />`**
   * Renders `historical_observations` as a solid line on the left and `hypothetical_projection_cone` (`p10_worst_case`, `p50_median_case`, `p90_best_case`, `rebalanced_p50`) as a shaded confidence cone on the right, plus displays `data.disclaimer`.
2. **`<ScenarioControlPanel scenario={scenarioState} onChange={setScenarioState} onRun={triggerAnalysis} />`**
   * Renders sliders for `market_decline_pct` (`-40%` to `0%`), `interest_rate_change_bps` (`-100` to `+200`), `currency_inr_usd_shift_pct` (`-15%` to `+15%`), preset buttons, and the custom AI prompt input box.
3. **`<CorrelationHeatmap matrixData={response.correlation_matrix} />`**
   * Renders the $N \times N$ correlation grid (`tickers` and `matrix`) color-coded from green (low/negative correlation) to red (`> 0.75` high correlation) and displays `high_correlation_warning`.