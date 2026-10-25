# Srujana Hackathon 2026 — F-06: Investment Portfolio Risk & Scenario Analysis

An interactive portfolio analysis solution that enables investors to understand asset allocation, concentration, volatility, and historical performance, simulate hypothetical macro stress tests (market crashes, RBI interest rate changes, sector disruptions, and INR/USD currency shifts), identify personal goal/liquidity conflicts, and evaluate rebalanced alternative allocations with transparent trade-offs.

---

## 1. Team Folder Sandbox & Roles

To ensure zero git merge collisions, team members operate strictly within their designated sandboxes as defined in [`CONTRACT.md`](CONTRACT.md):

| Teammate | Role | Allowed Sandboxes |
| :--- | :--- | :--- |
| **1. Lead** | **Quant + AI Engine & Repo Lead** | `/backend/engine/` (`quant.py`, `ai_agent.py`, `__init__.py`) |
| **2. Zama** | **FastAPI Server, DB & Mock Data** | `/backend/main.py`, `/backend/database.py`, `/mock-data/` |
| **3. Ahmad** | **Frontend Lead (App Shell & Pages)** | `/frontend/src/pages/`, `/frontend/src/App.tsx`, `/frontend/src/api/` |
| **4. Shyam** | **Visual Widgets + PPT & Video** | `/frontend/src/components/widgets/` |

---

## 2. Directory Structure

```text
Srujana_hackathon2026/
├── backend/
│   ├── engine/                     # Lead's Sandbox (Quant & AI logic)
│   │   ├── __init__.py
│   │   ├── quant.py
│   │   └── ai_agent.py
│   ├── main.py                     # Zama's Sandbox (FastAPI API server)
│   ├── database.py                 # Zama's Sandbox (Database/store)
│   └── requirements.txt            # Python dependencies
├── frontend/
│   └── src/
│       ├── api/                    # Ahmad's Sandbox (API client)
│       ├── pages/                  # Ahmad's Sandbox (Page views & layout)
│       ├── components/
│       │   └── widgets/            # Shyam's Sandbox (Isolated visual widgets)
│       └── App.tsx                 # Ahmad's Sandbox (Main App shell)
├── mock-data/                      # Zama's Sandbox (portfolios.json)
├── tests/                          # Automated test suites
├── CONTRACT.md                     # Master API schemas & folder rules
├── PROBLEM_STATEMENT.md            # Srujana problem specification
├── .gitignore                      # Ignore rules for Python, Node, Vite
└── README.md
```

---

## 3. Recommended Git Branching Strategy

Each team member works on their dedicated feature branch:
- **Lead**: `feature/quant-ai-engine`
- **Zama**: `feature/fastapi-server`
- **Ahmad**: `feature/frontend-shell`
- **Shyam**: `feature/visual-widgets`

---

## 4. Getting Started

### Backend Setup

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Alternatively, from inside `backend/`:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### Trading Statistics Dashboard

The separate trading-statistics API and dashboard live in [`backend/trading_user_stats/`](backend/trading_user_stats/README.md). From the repository root, install its requirements and run it on port 8001:

```bash
python -m pip install -r backend/trading_user_stats/requirements.txt
python -m uvicorn trading_user_stats.app.api:app --app-dir backend --reload --port 8001
```

The Trading Journal API is mounted in the main FastAPI application under `/api/journal`. It supports trade entry and editing, per-trade P&L, analytics, and local rule-based reviews. Journal records are stored in a separate SQLite database at `backend/journal/trading_journal.sqlite3` by default; override the path with `TRADING_JOURNAL_DB_PATH`. The current application has no authentication system, so journal requests use a fixed demo identity and are not suitable for private multi-user production data until connected to real authentication.

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
