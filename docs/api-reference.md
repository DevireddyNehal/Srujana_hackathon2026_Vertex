# API Reference

The F-06 service is `backend.main:app`. Run it on port 8000 with Uvicorn. FastAPI exposes the generated schema at `/openapi.json` and interactive documentation at `/docs`. No F-06 endpoint requires an authentication header.

## F-06 endpoints

### `GET /health`

Returns `{ "status": "ok" }`. No side effect.

### `GET /api/portfolios`

Loads `mock-data/portfolios.json`, accepts either a wrapper object or bare list, validates it as `PortfolioFile`, and returns `{ "portfolios": [...] }`. Each portfolio requires an id, name, investor profile, and at least one asset. Missing, unreadable, invalid, or malformed portfolio data returns HTTP 500.

### `POST /api/analyze-scenario`

Runs the quant engine and deterministic insight rules, then saves the result in the process-local analysis dictionary.

Request JSON fields:

- `portfolio_id`: optional string metadata.
- `portfolio_name`: optional string metadata.
- `investor_profile`: required object with `horizon_years` greater than 0 and at most 100, `risk_tolerance` in `Low|Moderate|High`, `liquidity_need` in `Low|Medium|High`, and non-negative `target_goal_inr`.
- `assets`: required non-empty array. Each asset has non-empty bounded `ticker`, `name`, `sector`, `asset_class`, positive `amount_inr`, `liquidity_tag` in `Low|Medium|High`, and non-empty bounded `currency_exposure`. Tickers must be unique case-insensitively.
- `scenario`: required object. `market_decline_pct` is `-50..0`; `interest_rate_change_bps` is `-100..300`; `currency_inr_usd_shift_pct` is `-15..15`; each sector shock is `-60..60`; `custom_ai_prompt` is at most 2,000 characters. Unknown fields are rejected.

Example valid request:

```json
{
  "portfolio_id": "tech-heavy",
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
    "preset_name": "IT stress",
    "market_decline_pct": -15,
    "interest_rate_change_bps": 75,
    "sector_shocks": {"IT": -25},
    "currency_inr_usd_shift_pct": -5,
    "custom_ai_prompt": ""
  }
}
```

The successful response contains `summary`, `composition`, `correlation_matrix`, `chart_data`, and `ai_analysis`. `summary` includes total and stressed values, impact, weighted volatility, modeled maximum drawdown, diversification score, illiquid share, CVaR, pain index, and ulcer index when returned by the engine. `chart_data` separates historical observations from a hypothetical P10/P50/P90 cone. `ai_analysis` contains assumptions, conflict objects, and the alternative allocation.

Errors: HTTP 422 for Pydantic validation; 503 if the engine import is unavailable; 502 for missing or malformed engine output; 502 for uncaught scenario-analysis errors. A successful call has an in-memory storage side effect and no durable analysis-history endpoint.

### `GET /api/contagion/scenarios`

Returns `{ "scenarios": [...] }` from `get_available_contagion_scenarios`. Metadata includes scenario id, title, headline, magnitude description, default magnitude, slider range, and historical precedent. Returns 503 if the contagion engine is unavailable.

### `POST /api/contagion/simulate`

Request fields are `scenario_id` (default `oil_supply_disruption`), optional `portfolio` object or list, optional `assets` list, and optional `custom_magnitude_pct`. Unknown fields are ignored. If neither portfolio nor assets is provided, the route falls back to the first mock portfolio when available. The response contains scenario metadata, staged graph effects, portfolio summary, and false-diversification fields added by the route. Execution exceptions return HTTP 500; unavailable engine returns 503.

### `POST /api/reverse-stress-test`

Request fields are optional `portfolio` object/list, optional `assets` list, and `target_loss_pct` greater than 0 and at most 100, default 15. If no portfolio is supplied, the route falls back to the first mock portfolio. The response contains volatility, Mahalanobis distance, a Gaussian tail estimate, fragility ranking, most probable failure shocks, and narrative. Execution exceptions return HTTP 500; unavailable engine returns 503.

### `GET /butterfly`

Returns `backend/engine/contagion_visualizer.html` as HTML. Returns 404 when the file is absent.

## Mounted journal endpoints

The journal router is mounted at `/api/journal`. Its identity dependency always returns the literal demo identity `demo`.

- `POST /api/journal/trades`: accepts `TradeCreate`, returns 201. Required symbol, side, quantity, entry price, and timezone-aware opening timestamp; closing price and closing timestamp must be both present or both absent.
- `GET /api/journal/trades`: query `status=all|open|closed`, optional symbol, `limit` 1-200, and non-negative offset. Returns trades and pagination fields.
- `GET /api/journal/trades/{trade_id}`: returns the current demo user's trade or 404.
- `PATCH /api/journal/trades/{trade_id}`: accepts partial `TradeUpdate`, returns the updated trade, 422 for invalid changes, or 404.
- `DELETE /api/journal/trades/{trade_id}`: returns 204 or 404.
- `GET /api/journal/analytics`: analyzes closed trades for the demo identity.
- `POST /api/journal/trades/{trade_id}/review`: returns a local-rules review or 404.

Journal records are stored in SQLite table `journal_trades` at the configured path.

## Separate statistics API

The separate service on port 8001 exposes `GET /api/health`, `/api/accounts`, `/api/date-ranges`, `/api/overview`, `/api/stats`, `/api/daily-pnl`, and `/api/breakdown`, plus an unlisted static root. Its local README documents range values, session filters, demo-only restrictions, and query parameters.
