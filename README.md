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
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
