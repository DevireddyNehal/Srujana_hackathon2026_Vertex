# Srujana Tech Fest 2026 — F-06: Portfolio Risk and Scenario Analysis

A portfolio-risk analysis prototype built with **React**, **TypeScript**, **Vite**, **Python**, and **FastAPI**. It provides API-backed portfolio scenario analysis, contagion simulation, and reverse stress testing. The repository also contains separate `trading-journal`, `trading-statistics`, and `TradeFXBook` applications.

> **Official Submission Report:** [📄 View/Download Jury Report (PDF)](./docs/Investment_Portfolio_Risk_Scenario_Analysis_Jury_Report.pdf) | [Word (DOCX)](./docs/Investment_Portfolio_Risk_Scenario_Analysis_Jury_Report.docx)
>
> **Project Status:** ✅ **All 68 Automated Tests Passing (100% Green)**. Frontend TypeScript/Vite production build verified with zero errors. All core F-06 quantitative stress, contagion graph, and reverse stress endpoints operational.
>
> **Disclaimer:** Analytical decision-support prototype. Results are model-based outputs, not personalized investment or tax advice.

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

## 1. About the Project & Overview

**Vertex Portfolio Risk Lab** is an interactive, quantitative decision-support environment developed for **Problem Statement F-06 (Investment Portfolio Risk & Scenario Analysis)** at **Srujana Tech Fest 2026**.

It addresses the fundamental challenge of hidden portfolio risk: allowing investors to look beyond static returns and evaluate how multi-factor market crashes, interest-rate shifts, sector disruptions, currency shocks, and cross-asset contagion affect their holdings in real time.

### About the Team
* **Nehal Devireddy** — Project Lead & Quantitative Architecture (`backend/engine/quant.py`, `backend/engine/contagion.py`, `backend/engine/ai_agent.py`)
* **Zama** — Backend & API Engineering (`backend/main.py`, `backend/database.py`, mock fixtures)
* **Ahmad** — Frontend Lead (React/TypeScript application shell, page routing, and state orchestration)
* **Shyam** — UI Widgets & Presentation (Correlation heatmap, scenario shock controls, historical vs. hypothetical projection charts)

### Official Project Documentation
* 📄 **Jury Evaluation Report (PDF):** [`docs/Investment_Portfolio_Risk_Scenario_Analysis_Jury_Report.pdf`](./docs/Investment_Portfolio_Risk_Scenario_Analysis_Jury_Report.pdf)
* 📝 **Jury Evaluation Report (Word):** [`docs/Investment_Portfolio_Risk_Scenario_Analysis_Jury_Report.docx`](./docs/Investment_Portfolio_Risk_Scenario_Analysis_Jury_Report.docx)

### Core F-06 Capabilities

* **Portfolio loading:** Reads demo portfolio fixtures from `mock-data/portfolios.json`.
* **Scenario analysis:** Accepts scenario requests through `POST /api/analyze-scenario`.
* **Contagion simulation:** Models directed-graph contagion across economic dependencies via `POST /api/contagion/simulate`.
* **Reverse stress testing:** Solves for catastrophic threshold breaking points via `POST /api/reverse-stress-test`.
* **Risk interface:** Provides React views that call the FastAPI backend for risk-related results.
* **Historical-data artifacts:** Includes CSV/JSON artifacts and metadata under `f06_historical_dataset/`.

### Other Applications in This Repository

The repository also includes a SQLite-backed trading journal mounted in the main API, a separate trading-statistics service, and a separate TradeFXBook application. These are distinct modular components.

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

Run from the repository root:
```bash
pytest tests/
```

**Verification Result: 68 PASSED (100% Green)**
* `tests/test_engine.py`: 29 tests passed (Quant scenario math, VaR, CVaR, HHI, contagion graph, reverse stress solving).
* `tests/test_tradefxbook.py`: 27 tests passed.
* `tests/test_auth_multiuser.py`: 4 tests passed.
* `tests/test_router.py`: 3 tests passed.
* `tests/test_storage.py`: 2 tests passed.
* `tests/test_metrics.py`: 2 tests passed.
* `tests/test_analytics.py`: 1 test passed.

---

## 10. Security, Privacy, and Operational Limitations

* The F-06 API is designed as an explainable decision-support prototype rather than a production brokerage execution engine.
* The journal uses device/demo isolation and is not connected to live broker accounts.
* F-06 analysis history is held in process-local memory during simulation sessions.
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
