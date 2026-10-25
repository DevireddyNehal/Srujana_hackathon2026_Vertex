# Setup Guide

## Verified environment facts

The repository declares Python dependencies but does not declare a supported Python version. The current verification used Python 3.14 and Node/npm available in the workspace. Treat those versions as observed, not as a project support guarantee. The frontend requires Node.js and npm; no engine constraint is declared in `frontend/package.json`.

## F-06 backend: PowerShell

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Expected endpoints: `http://127.0.0.1:8000/health`, `/docs`, and `/openapi.json`. Startup initializes the process-local analysis interface and the SQLite journal schema.

The backend runtime manifest does not include `httpx`, which is used by the test client, and does not include `pydantic-settings`, which is imported by TradeFXBook. This is a verified manifest gap, not a reason to modify application code silently.

## F-06 backend: Bash

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

## Frontend: PowerShell

Run from `frontend/`:

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env.local` if the backend is not at `http://localhost:8000`. Vite prints the actual local URL. The frontend build and lint commands were executed successfully in this environment.

## Frontend: Bash

Run from `frontend/`:

```bash
npm install
cp .env.example .env.local
npm run dev
```

## Tests

From the repository root:

```powershell
python -m pytest -q
```

For F-06 tests, the current backend manifest is incomplete because it omits `httpx`, which `fastapi.testclient` uses. Install the F-06 runtime manifest and the missing test dependency in the same virtual environment:

```powershell
python -m pip install -r backend/requirements.txt
python -m pip install httpx
```

The repository-level `requirement.txt` additionally declares `pydantic-settings` for TradeFXBook, but it is not the F-06 backend manifest. Do not merge separate application environments without checking version compatibility.

Frontend checks from `frontend/`:

```powershell
npm run lint
npm run build
```

## Other services

Trading statistics, from the repository root:

```powershell
python -m pip install -r backend/trading_user_stats/requirements-dev.txt
python -m uvicorn trading_user_stats.app.api:app --app-dir backend --reload --port 8001
```

Its `requirements-dev.txt` includes the service runtime requirements plus pytest and HTTPX, so it is the correct manifest for running the statistics tests. The runtime-only manifest is `backend/trading_user_stats/requirements.txt`. Startup seeds synthetic data by default.

TradeFXBook has no dedicated requirements file in the repository. Its `config.py` imports `pydantic-settings`; the root `requirement.txt` declares that package along with general runtime/test packages. Starting it with `python run_tradefxbook.py --port 8080` is therefore dependent on that root environment and has not been verified from a clean install.

## Exact F-06 smoke command

The following PowerShell command was run from the repository root using the active Python environment. It exercises the health, portfolio, OpenAPI, scenario, contagion, and reverse-stress routes in-process:

```powershell
@'
import json
from fastapi.testclient import TestClient
from backend.main import app

with open("mock-data/portfolios.json", encoding="utf-8") as file:
	portfolio = json.load(file)["portfolios"][0]

scenario = {
	"investor_profile": portfolio["investor_profile"],
	"assets": portfolio["assets"],
	"scenario": {
		"preset_name": "Smoke Test",
		"market_decline_pct": -15,
		"interest_rate_change_bps": 75,
		"sector_shocks": {"IT": -25},
		"currency_inr_usd_shift_pct": -5,
		"custom_ai_prompt": ""
	}
}

with TestClient(app) as client:
	print(client.get("/health").status_code)
	print(client.get("/api/portfolios").status_code)
	print(client.get("/openapi.json").status_code)
	print(client.post("/api/analyze-scenario", json=scenario).status_code)
	print(client.post("/api/contagion/simulate", json={"scenario_id": "oil_supply_disruption", "assets": portfolio["assets"]}).status_code)
	print(client.post("/api/reverse-stress-test", json={"target_loss_pct": 15, "assets": portfolio["assets"]}).status_code)
'@ | python -
```

This is an in-process API check, not proof of a separately started frontend/backend browser workflow.

## Configuration

Verified environment variables are `CORS_ORIGINS`, `LOG_LEVEL`, `TRADING_JOURNAL_DB_PATH`, `TRADING_STATS_DEMO_TRADE_COUNT`, `TRADING_STATS_SEED_DEMO`, `TRADING_STATS_DB_PATH`, `APP_ENV`, `TRADING_DB`, and frontend `VITE_API_BASE_URL`. TradeFXBook settings use the `TRADEFXBOOK_` prefix. Never copy the hard-coded demo secret values from source into a deployment.

## Troubleshooting

- `ModuleNotFoundError: pydantic_settings`: install the dependency used by `tradefxbook/config.py`; it is present in root `requirement.txt` but absent from `backend/requirements.txt`.
- Frontend API connection errors: start port 8000 and use an API origin reachable from the browser.
- Missing portfolio data: run from the repository root and confirm `mock-data/portfolios.json` exists.
- Statistics startup cost: set `TRADING_STATS_SEED_DEMO=false` for a non-seeding local run.
