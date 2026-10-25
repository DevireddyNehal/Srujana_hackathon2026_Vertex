# Srujana Tech Fest 2026 — F-06: Portfolio Risk and Scenario Analysis

A portfolio-risk analysis prototype built with **React**, **TypeScript**, **Vite**, **Python**, and **FastAPI**. It provides API-backed portfolio scenario analysis, contagion simulation, and reverse stress testing. The repository also contains separate `trading-journal`, `trading-statistics`, and `TradeFXBook` applications.

> **Project Status:** Core F-06 routes and the frontend build have passed the checks described below. A complete browser-to-backend demonstration against separately running services and the full Python test suite have not yet been verified.
>
> **Disclaimer:** Results are analytical model outputs, not investment, legal, or tax advice.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Repository Structure](#3-repository-structure)
4. [Run the F-06 Application Locally](#4-run-the-f-06-application-locally)
5. [API Reference](#5-api-reference)
6. [Run the Separate Applications](#6-run-the-separate-applications)
7. [Architecture](#7-architecture)
8. [Data and Configuration](#8-data-and-configuration)
9. [Testing and Verification](#9-testing-and-verification)
10. [Security, Privacy, and Operational Limitations](#10-security-privacy-and-operational-limitations)
11. [Documentation](#11-documentation)
12. [Hackathon Submission Checklist](#12-hackathon-submission-checklist)

---

## 1. Project Overview

**F-06** focuses on examining how specified market scenarios and adverse conditions may affect a portfolio. Users can load demo portfolios, submit scenarios for analysis, explore contagion simulations, and run reverse stress tests through the web interface and FastAPI service.

The repository is a prototype, not a production investment platform. Its results depend on the supplied data, scenario assumptions, and implemented analytical methods. They should not be interpreted as guaranteed forecasts or personalized investment recommendations.

### Core F-06 Capabilities

* **Portfolio loading:** Reads demo portfolio fixtures from `mock-data/portfolios.json`.
* **Scenario analysis:** Accepts scenario requests through `POST /api/analyze-scenario`.
* **Contagion simulation:** Provides scenario discovery and simulation endpoints for portfolio contagion analysis.
* **Reverse stress testing:** Exposes an endpoint for evaluating reverse-stress requests.
* **Risk interface:** Provides React views that call the FastAPI backend for risk-related results.
* **Historical-data artifacts:** Includes CSV/JSON artifacts and metadata under `f06_historical_dataset/`.

### Other Applications in This Repository

The repository also includes a SQLite-backed trading journal mounted in the main API, a separate trading-statistics service, and a separate TradeFXBook application. These are distinct components and should not be presented as features of the F-06 risk engine unless they are explicitly included in the demonstrated workflow.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React, TypeScript, Vite | Interface, portfolio views, controls, charts, and API client |
| **API Backend** | Python, FastAPI, Uvicorn, Pydantic | HTTP endpoints, request validation, orchestration, and OpenAPI documentation |
| **Risk Engine** | Python modules in `backend/engine/` | Scenario stress analysis, contagion simulation, reverse stress testing, and related heuristics |
| **Storage** | SQLite and process-local Python memory | Persistent journal records and temporary F-06 analysis records |
| **Demo Inputs** | JSON fixtures and synthetic trade records | Reproducible demonstration inputs |
| **Historical Artifacts** | CSV and JSON | Downloaded market-data artifacts and data-quality metadata |

### Trade-Prediction Model Status

A supervised trade-prediction model is **not** currently implemented or verified in this repository. The F-06 natural-language scenario parser uses deterministic keyword/rule logic; the inspected implementation does not establish a trained machine-learning model, model-training pipeline, prediction endpoint, backtest, or validated predictive performance.

A future extension could evaluate a classifier such as Random Forest using historical OHLCV data, lagged returns, volatility, and other documented features. Any future model should specify its prediction target and horizon, use time-ordered training/testing, avoid future-data leakage, and report measured out-of-sample metrics. Do not describe this proposed extension as an existing feature or claim a prediction rate without reproducible evidence.

---

## 3. Repository Structure

This is a key directory overview, not an exhaustive file listing. Generated build output, virtual environments, caches, and local database files are omitted.

```text
Srujana_hackathon2026/
├── backend/
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── quant.py
│   │   ├── ai_agent.py
│   │   └── contagion.py
│   ├── main.py                  # Main F-06 FastAPI application
│   ├── database.py              # Process-local analysis storage
│   ├── journal/                 # SQLite trading journal
│   ├── trading_user_stats/      # Separate statistics service
│   └── requirements.txt         # Main backend dependencies
├── tradefxbook/                 # Separate TradeFXBook application
├── run_tradefxbook.py           # TradeFXBook entry point
├── requirement.txt              # Root-level dependency manifest
├── f06_historical_dataset/      # Historical-data files and metadata
├── frontend/
│   ├── package.json
│   ├── .env.example
│   └── src/
│       ├── api/                 # API client
│       ├── pages/               # Page views and layout
│       ├── components/widgets/  # Visual widgets
│       └── App.tsx              # Main application shell
├── mock-data/                   # Demo portfolio fixtures
├── tests/                       # Automated test suites
├── docs/                        # Technical and audit documentation
├── CONTRACT.md                  # API schemas and folder conventions
├── PROBLEM_STATEMENT.md         # F-06 problem specification
├── .gitignore
└── README.md
```

---

## 4. Run the F-06 Application Locally

### Prerequisites

* **Python** installed and compatible with the dependencies in `backend/requirements.txt`.
* **Node.js** and **npm** installed.
* A terminal capable of running the commands for your operating system.

*Note: The repository does not establish a single verified runtime-version matrix. Use versions compatible with the checked-in dependency manifests and verify them in the target environment.*

### Step 1: Start the Backend

Run from the repository root.

**Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

**Linux or macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

The main API should be available at `http://127.0.0.1:8000`.
* **Interactive API documentation:** `http://127.0.0.1:8000/docs`
* **OpenAPI schema:** `http://127.0.0.1:8000/openapi.json`
* **Health endpoint:** `http://127.0.0.1:8000/health`

### Step 2: Configure the Frontend

Open a second terminal from the repository root.

**Windows PowerShell:**
```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
```

**Linux or macOS:**
```bash
cd frontend
npm install
cp .env.example .env.local
```

Check `frontend/.env.local` and set the API origin to the running backend if needed:
```env
VITE_API_BASE_URL=http://localhost:8000
```

> **Security Note:** Do not put secrets in Vite environment variables intended for browser code; values prefixed with `VITE_` are exposed to the frontend bundle.

### Step 3: Start the Frontend

From the `frontend/` directory:
```bash
npm run dev
```

Open the local URL printed by Vite in the terminal. The frontend and API must both be running. The API must also allow browser requests from the frontend origin through its CORS configuration.

### Suggested Demo Workflow

1. Confirm the API `/health` endpoint responds.
2. Open the frontend using the URL printed by Vite.
3. Load a demo portfolio.
4. Submit a scenario and inspect the returned risk analysis.
5. Open the contagion view and run a simulation.
6. Open the reverse stress-test view and submit a request.

*Note: This is a suggested workflow, not a claim that the entire browser-to-backend sequence has already passed end-to-end testing. Verify it in the environment used for the presentation before describing it as a tested demo.*

---

## 5. API Reference

The primary F-06 FastAPI application exposes the following routes in the current implementation:

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check |
| `GET` | `/api/portfolios` | Retrieve available demo portfolios |
| `POST` | `/api/analyze-scenario` | Submit a scenario-analysis request |
| `GET` | `/api/contagion/scenarios` | List available contagion scenarios |
| `POST` | `/api/contagion/simulate` | Run a contagion simulation |
| `POST` | `/api/reverse-stress-test` | Run reverse stress testing |
| `GET` | `/butterfly` | Butterfly view/route exposed by the application |

Use `/docs` or `/openapi.json` to inspect the current request and response schemas. Refer to `CONTRACT.md` and `docs/api-reference.md` for repository-specific API details. Exact request examples should be copied from the verified schema rather than guessed.

### Trading Journal API

The trading journal is mounted under `/api/journal` in the main FastAPI application. It supports trade creation, listing, retrieval, updates, deletion, analytics, and per-trade rule-based reviews. Consult the generated OpenAPI schema for exact subpaths and request models.

Journal records are stored in a separate SQLite database. The default path is `backend/journal/trading_journal.sqlite3`; configure `TRADING_JOURNAL_DB_PATH` to override it.

> **Authentication Limitation:** The current journal uses a fixed/demo identity and does not provide production user authentication or a multi-user authorization boundary. Do not store private or sensitive real trading records in this setup.

---

## 6. Run the Separate Applications

These services are optional and are not required merely to start the primary F-06 API, unless a specific demonstration depends on them. Run them in separate terminals.

### Trading Statistics Dashboard

From the repository root:
```bash
python -m pip install -r backend/trading_user_stats/requirements-dev.txt
python -m uvicorn trading_user_stats.app.api:app --app-dir backend --reload --port 8001
```

* Open `http://127.0.0.1:8001/` for the dashboard and `http://127.0.0.1:8001/docs` for API documentation.
* The service uses its own SQLite database and synthetic demo trades; startup seeds 100,000 synthetic trades by default.
* See `backend/trading_user_stats/README.md` for service-specific details.

### TradeFXBook

From the repository root:
```bash
python -m pip install -r requirement.txt
python run_tradefxbook.py --port 8080
```

* Open `http://localhost:8080/` for the dashboard, `/docs` for OpenAPI, or `/redoc` for ReDoc.
* The root `requirement.txt` is a shared manifest, not a dedicated TradeFXBook lockfile.
* Review the application's configuration and replace any source-code demo secret defaults before deployment beyond a local demonstration.

---

## 7. Architecture

```text
Browser
  │
  ▼
React + TypeScript + Vite (frontend/)
  │
  │ HTTP API requests
  ▼
FastAPI application (backend/main.py)
  ├──► backend/engine/quant.py
  ├──► backend/engine/ai_agent.py
  ├──► backend/engine/contagion.py
  ├──► mock-data/portfolios.json
  ├──► process-local F-06 analysis store
  └──► /api/journal ──► SQLite journal database

Separate services:
  • Trading Statistics ──► separate FastAPI app + SQLite database
  • TradeFXBook        ──► separate application entry point
```

The frontend also contains local illustrative portfolio data and calculations. API-backed risk views call the main backend and report connection or server errors rather than silently substituting successful sample responses. The natural-language scenario parser is deterministic keyword/rule logic; an integrated external LLM provider is not verified in the inspected implementation.

---

## 8. Data and Configuration

### Data Inputs

* **Demo portfolios:** `mock-data/portfolios.json`.
* **Historical artifacts:** Files and metadata under `f06_historical_dataset/`.
* **Trading statistics:** Synthetic demo trades generated by the separate statistics service.
* **Analysis storage:** F-06 analysis records are process-local and are lost when the main API process restarts.
* **Journal storage:** SQLite, using `TRADING_JOURNAL_DB_PATH` or the documented default path.

The historical dataset metadata identifies Yahoo Finance's unofficial chart endpoint as a source and records data-quality and redistribution limitations. Check the metadata accompanying each dataset before reuse. The presence of historical observations does not establish completeness, a live feed, or permission to redistribute data.

### Environment Variables

| Variable | Component | Purpose |
| :--- | :--- | :--- |
| `CORS_ORIGINS` | Main FastAPI backend | Allowed browser origins |
| `LOG_LEVEL` | Main FastAPI backend | Logging level |
| `VITE_API_BASE_URL` | Frontend | Base origin used for API requests |
| `TRADING_JOURNAL_DB_PATH` | Trading journal | Optional SQLite database path override |

Keep real credentials and local environment values out of version control. Do not place private secrets in `VITE_` variables because they are shipped to the browser.

---

## 9. Testing and Verification

### Frontend Checks

Run from `frontend/`:
```bash
npm run lint
npm run build
```

These checks passed in the environment last checked on **25 October 2026**. No frontend unit-test or browser end-to-end test script was declared at that time.

### Python Checks

Run from the repository root, inside the intended Python environment:
```bash
python -m pytest -q
```

> **Known Test Blocker:** The full Python test run stopped during collection because `tests/test_tradefxbook.py` imports `pydantic-settings`, which was missing from the active interpreter. A full-suite pass is therefore not claimed. Install the appropriate project/test dependencies in the environment used for testing, then rerun the suite and record the result.

F-06 health, portfolio loading, OpenAPI generation, scenario analysis, contagion simulation, and reverse-stress smoke checks passed in-process through FastAPI `TestClient`. These checks do not replace a complete browser workflow against separately running services. The smoke-check command is recorded in `docs/testing.md`.

---

## 10. Security, Privacy, and Operational Limitations

* The F-06 API does not have a real authentication or authorization boundary.
* The journal uses a fixed/demo identity and is not safe for private multi-user production data.
* F-06 analysis history is held in process-local memory and is lost after restart.
* Full Python test-suite completion is not verified because of the dependency issue described above.
* Browser-to-backend integration against separately launched services has not been verified end-to-end.
* The repository does not establish a production deployment configuration, backup/restore plan, monitoring, rate limiting, load testing, or CI workflow.
* No repository license was found in the inspected project state; do not assume the code is licensed for unrestricted reuse.
* Historical/demo inputs and analytical results do not guarantee future returns or establish investment performance.
* `TradeFXBook` contains source-code demo secret defaults that must be replaced before deployment beyond a local demo.

**Do not use this prototype as the sole basis for real investment decisions or expose it to untrusted users without appropriate security, validation, privacy, and operational controls.**

---

## 11. Documentation

The repository includes the following supporting documents (confirm that each linked file exists in the submitted repository and that its contents match the final implementation):

* [Audit Summary](docs/audit-summary.md)
* [Architecture](docs/architecture.md)
* [Setup Guide](docs/setup.md)
* [API Reference](docs/api-reference.md)
* [Risk Engine](docs/risk-engine.md)
* [Data Sources](docs/data-sources.md)
* [Testing](docs/testing.md)
* [Security and Privacy](docs/security-privacy.md)
* [Known Limitations](docs/known-limitations.md)
* [AI Usage](docs/ai-usage.md)
* [Submission Checklist](docs/submission-checklist.md)
* [API and Folder Contract](CONTRACT.md)
* [Problem Statement](PROBLEM_STATEMENT.md)

---

## 12. Hackathon Submission Checklist

Before the presentation or final submission:

- [ ] Install dependencies in a clean environment and verify the documented startup commands.
- [ ] Run the frontend lint and production build.
- [ ] Resolve the Python test dependency issue (`pydantic-settings`) and rerun the full test suite, or disclose the unresolved failure.
- [ ] Verify the complete browser-to-backend workflow using the exact environment intended for judging.
- [ ] Confirm the demo URL, runtime versions, and required startup order.
- [ ] Review historical-data attribution, applicable terms, missing-data handling, and redistribution restrictions.
- [ ] Complete the team's AI-tool/model-use disclosure accurately.
- [ ] Confirm team members' names, contributions, and code ownership.
- [ ] Add an appropriate repository license if one is required and intended by the team.
- [ ] Remove development credentials and replace demo secrets before any non-local deployment.
- [ ] Keep planned features, including any future trade-prediction model, separate from verified implemented features.

---

*Last implementation-status review: 25 October 2026.*
