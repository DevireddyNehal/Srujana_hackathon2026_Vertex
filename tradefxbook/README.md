# TradeFXBook — Trading Journal, Analytics, and Demo Dataset

**TradeFXBook** is a production-grade Trading Journal and Quantitative Analytics platform equipped with a deterministic, reproducible synthetic demo dataset of **exactly 10 demo traders** and **exactly 100,000 closed demo trade records** in total (10,000 closed trades per trader).

---

## 1. Architecture & Design Principles

TradeFXBook is implemented as a clean, self-contained, high-performance module designed to preserve any surrounding repositories while providing full-stack trading journal capabilities:

- **Isolated & Modular:** Implemented inside `/tradefxbook/` with dedicated configuration, models, database schemas, calculation engines, API routers, and front-end interface.
- **Strict User Isolation:** Demo Trader 01 to Demo Trader 10 operate as completely isolated accounts. One trader cannot view, query, update, or export another trader's records.
- **Indexed Database Engine:** Backed by SQLite in Write-Ahead Logging (`WAL`) mode with memory temp storage, foreign keys, and composite indexes on `(user_id, status, exit_time)`, `(user_id, symbol)`, and `(user_id, strategy_or_setup)`.
- **Database Aggregations:** Computes portfolio metrics and daily summaries via SQL aggregations in under 100ms across 10,000 trades, avoiding binary floating-point discrepancies and eliminating the need to load 100,000 rows into memory for dashboard queries.
- **Deterministic & Idempotent Seeding:** Generates the exact same 100,000 trades and 10 trader accounts using a fixed random seed (`seed=42`) and a fixed reference end date (`2026-10-25T00:00:00Z`). Re-running the seed process is strictly idempotent.

```text
tradefxbook/
├── __init__.py           # Package marker and version info
├── config.py             # Central settings (DB paths, seed constants, JWT, ports)
├── database.py           # SQLite connection pool, WAL mode, schema initialization, indexes
├── models.py             # Pydantic schemas for Trades, Metrics, Daily P&L, Breakdowns
├── calculations.py       # Authoritative financial math engine (gross/net P&L, R:R, drawdown, win rate)
├── generator.py          # Deterministic seed generator (10 users, 10k trades each, 10 personas)
├── repository.py         # Fast database repository with SQL aggregations and pagination
├── auth.py               # Authentication, user context, and demo switcher dependency
├── api.py                # FastAPI app and REST routes (/api/v1/trades, /api/v1/analytics, /admin)
├── cli.py                # CLI commands: seed, verify, reset, serve
├── verify.py             # Standalone verification script inspecting database counts directly
├── static/               # Modern dark-mode responsive trading terminal front-end
│   ├── index.html        # UI shell with KPI cards, Chart.js canvases, Trade Journal table
│   ├── styles.css        # High-density trading dashboard stylesheet
│   └── app.js            # Client state, Chart.js integrations, trader switcher, CRUD modals
└── data/
    └── tradefxbook.db    # High-performance SQLite database file (WAL mode)
```

---

## 2. 10 Demo Trader Accounts (Exact Distribution)

Each demo trader features a distinct behavioral profile, trade frequency, risk profile, and trading session:

| Trader ID | Display Name | Trading Persona | Starting Balance | Primary Instruments | Target Win Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `demo_trader_01` | **Demo Trader 01** | Conservative Swing Trader | $50,000.00 | EUR/USD, GBP/USD | ~62% |
| `demo_trader_02` | **Demo Trader 02** | High-Frequency Scalper | $25,000.00 | EUR/USD, USD/JPY | ~52% |
| `demo_trader_03` | **Demo Trader 03** | Trend Follower & Index Runner | $100,000.00 | US30, XAU/USD (Gold) | ~43% (Asymmetric R:R) |
| `demo_trader_04` | **Demo Trader 04** | Breakout Specialist | $50,000.00 | GBP/USD, EUR/USD | ~49% |
| `demo_trader_05` | **Demo Trader 05** | Asian Mean Reversion Trader | $30,000.00 | USD/JPY, AUD/USD | ~66% |
| `demo_trader_06` | **Demo Trader 06** | Crypto & Momentum Trader | $20,000.00 | BTC/USD, ETH/USD | ~45% |
| `demo_trader_07` | **Demo Trader 07** | Emotional / Inconsistent Trader | $50,000.00 | XAU/USD, US30 | ~38% (Negative Net P&L) |
| `demo_trader_08` | **Demo Trader 08** | Institutional Systematic Trader | $250,000.00 | EUR/USD, Gold | ~57% (Steady low-DD) |
| `demo_trader_09` | **Demo Trader 09** | News Event Volatility Trader | $40,000.00 | GBP/USD, US30 | ~50% (High slippage) |
| `demo_trader_10` | **Demo Trader 10** | Algorithmic Grid/Session Trader | $60,000.00 | EUR/USD, USD/JPY | ~60% |

All seeded records have `is_demo = 1` and `seed_batch = 'tradefxbook_demo_batch_v1'`.

---

## 3. Database Verification Results (Actual Records)

Running the verification script inspects the SQLite database directly:

```bash
python3 -m tradefxbook.cli verify
```

### Actual Output from Database:
```text
================================================================================
          TRADEFXBOOK DEMO DATASET INTEGRITY VERIFICATION REPORT
================================================================================
Database File:               .../tradefxbook/data/tradefxbook.db
Seed Batch Identifier:       tradefxbook_demo_batch_v1
Total Demo Users:            10 (Expected: 10)
Total Seeded Demo Trades:    100,000 (Expected: 100,000)
Total Closed Demo Trades:    100,000 (Expected: 100,000)
Distinct Trade IDs:          100,000 (Expected: 100,000)
Timestamp Anomalies:         0 (Expected: 0)
Orphan Trades:               0 (Expected: 0)
--------------------------------------------------------------------------------
PER-TRADER BREAKDOWN (10,000 Closed Trades per User):
User ID        | Total Trades | Closed Trades | Wins  | Losses | BE   | Net P&L (USD)
---------------+--------------+---------------+-------+--------+------+--------------
demo_trader_01 | 10,000       | 10,000        | 6,267 | 3,732  | 1    | $15,365,290.50
demo_trader_02 | 10,000       | 10,000        | 5,456 | 4,543  | 1    | $3,118,164.35
demo_trader_03 | 10,000       | 10,000        | 4,350 | 5,617  | 33   | $40,858,799.01
demo_trader_04 | 10,000       | 10,000        | 5,104 | 4,896  | 0    | $12,837,564.11
demo_trader_05 | 10,000       | 10,000        | 6,823 | 3,177  | 0    | $5,440,743.82
demo_trader_06 | 10,000       | 10,000        | 4,518 | 5,307  | 175  | $1,209,833.56
demo_trader_07 | 10,000       | 10,000        | 3,851 | 6,103  | 46   | $-4,017,779.87
demo_trader_08 | 10,000       | 10,000        | 5,736 | 4,264  | 0    | $66,775,998.15
demo_trader_09 | 10,000       | 10,000        | 5,045 | 4,896  | 59   | $10,165,531.18
demo_trader_10 | 10,000       | 10,000        | 6,183 | 3,816  | 1    | $8,743,977.58
--------------------------------------------------------------------------------
INTEGRITY CHECKS SUMMARY:
  [PASS] EXACT_10_DEMO_USERS
  [PASS] EXACT_100000_TOTAL_DEMO_TRADES
  [PASS] EXACT_100000_CLOSED_DEMO_TRADES
  [PASS] EXACT_10000_TRADES_PER_USER
  [PASS] ALL_TRADE_IDS_UNIQUE
  [PASS] NO_TIMESTAMP_ANOMALIES
  [PASS] NO_ORPHAN_TRADES
  [PASS] SEED_BATCH_MATCHES
================================================================================
>>> OVERALL STATUS: ALL 100,000 DEMO TRADE INTEGRITY CHECKS PASSED SUCCESSFULLY! <<<
================================================================================
```

---

## 4. Authoritative Financial Calculations

### 1. Realized Trade P&L
For standard Forex pairs (EUR/USD, GBP/USD, etc.), Commodities (Gold), Indices, and Crypto:
- **Long Gross P&L:** `(exit_price - entry_price) * quantity * contract_size`
- **Short Gross P&L:** `(entry_price - exit_price) * quantity * contract_size`

For pairs where the quote currency is JPY (e.g., USD/JPY) and the account currency is USD:
- **Long Gross P&L:** `((exit_price - entry_price) / exit_price) * quantity * contract_size`
- **Short Gross P&L:** `((entry_price - exit_price) / exit_price) * quantity * contract_size`

### 2. Net Realized P&L
```text
net_pnl = gross_pnl - commission - other_fees + signed_swap_adjustment
```
- `commission` and `other_fees` are non-negative costs.
- `signed_swap_adjustment` is a signed cash flow (positive adds cash; negative reduces cash).

### 3. Win Rate (Excluding Breakeven Trades)
```text
win_rate = (winning_trades / (winning_trades + losing_trades)) * 100
```
- **Winning Trade:** `net_pnl > 0.0`
- **Losing Trade:** `net_pnl < 0.0`
- **Breakeven Trade:** `net_pnl == 0.0` (strictly excluded from the win rate denominator).

### 4. Profit Factor
```text
profit_factor = sum(positive net P&L) / abs(sum(negative net P&L))
```
- When there are no losing trades, the undefined/infinite case is handled safely by returning `None` / `N/A` without raising exceptions or emitting invalid JSON.

### 5. Expectancy
```text
expectancy = sum(net P&L) / total_closed_trades
```
- Includes all winning, losing, and breakeven trades.

### 6. Maximum Drawdown (Peak-to-Trough)
Calculated chronologically across the realized equity curve:
- `equity_0 = starting_balance`
- `equity_i = equity_{i-1} + net_pnl_i`
- `high_water_mark_i = max(high_water_mark_{i-1}, equity_i)`
- `drawdown_currency_i = high_water_mark_i - equity_i`
- `drawdown_pct_i = (drawdown_currency_i / high_water_mark_i) * 100`
- `max_drawdown_currency = max(drawdown_currency_i)`
- `max_drawdown_pct = max(drawdown_pct_i)`

### 7. Continuous Daily P&L Series
- Assigns P&L to trade exit dates converted to the user's configured timezone.
- Generates every calendar day in the selected date range.
- Inactive trading days, weekends, and holidays are returned as zero-P&L days (`net_pnl = 0.0`, `closed_trades = 0`).
- Reconciles exactly: the sum of daily net P&Ls equals the total net P&L of all closed trades in that date range.

---

## 5. Setup & Execution Commands

### Prerequisites
- Python 3.10+ (tested on Python 3.14.4)
- `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `pytest`

### A. Install Dependencies
```bash
pip install fastapi uvicorn pydantic pydantic-settings pytest
```

### B. Seed the Demo Dataset (100,000 Trades)
```bash
python3 -m tradefxbook.cli seed
```
To force a reseed:
```bash
python3 -m tradefxbook.cli seed --force
```

### C. Verify Database Counts and Dataset Integrity
```bash
python3 -m tradefxbook.cli verify
```

### D. Start the Application Server
Run via the convenience script:
```bash
python3 run_tradefxbook.py --port 8080
```
Or via the CLI module:
```bash
python3 -m tradefxbook.cli serve --port 8080
```

### E. Run the Automated Test Suite
```bash
python3 -m pytest tests/test_tradefxbook.py -v
```
To run all project tests:
```bash
python3 -m pytest
```

### F. Safely Reset Demo Data
Removes only demo records (`is_demo = 1` or matching the demo batch identifier), strictly preserving non-demo real users and real trades:
```bash
python3 -m tradefxbook.cli reset --confirm
```

---

## 6. Accessing the UI & REST API Locally

Once the application is running:

- **Web Dashboard & Journal:** [http://localhost:8080/](http://localhost:8080/)
- **Interactive OpenAPI Documentation:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **ReDoc API Documentation:** [http://localhost:8080/redoc](http://localhost:8080/redoc)

### Switching Demo Traders in the UI
The top-center dropdown allows instant switching between `Demo Trader 01` through `Demo Trader 10`. The entire dashboard (KPI cards, Daily P&L chart, Realized Equity Curve, Breakdown by strategy/session, and Trade History table) instantly updates to reflect only that trader's records.

---

## 7. REST API Endpoints Reference

### Authentication & Switcher
- `GET /api/v1/auth/me`: Get current authenticated user profile and balance.
- `GET /api/v1/auth/demo-users`: List the 10 seeded demo traders with metadata.
- `POST /api/v1/auth/switch-demo/{user_id}`: Switch the active demo user session.

### Trade Journal Management
- `GET /api/v1/trades`: Paginated and filterable trade list (`page`, `page_size`, `sort_by`, `sort_order`, `symbol`, `direction`, `outcome`, `strategy`, `session`, `search`, `date_from`, `date_to`).
- `POST /api/v1/trades`: Create a new trade entry with authoritative calculations.
- `GET /api/v1/trades/{trade_id}`: Retrieve full details of an individual trade (user isolated).
- `PUT /api/v1/trades/{trade_id}`: Update an individual trade and recalculate metrics.
- `DELETE /api/v1/trades/{trade_id}`: Delete an individual trade record.
- `GET /api/v1/trades/export/csv`: Export filtered trade history to CSV (user isolated).

### Analytics & Reporting
- `GET /api/v1/analytics/overview`: 22 performance metrics + secondary statistics (`range_preset`: 7d, 30d, 90d, ytd, 1y, all, custom).
- `GET /api/v1/analytics/daily-pnl`: Continuous daily P&L series with zero-days included.
- `GET /api/v1/analytics/equity-curve`: Realized equity points and peak-to-trough drawdowns.
- `GET /api/v1/analytics/breakdown`: Aggregated breakdowns by strategy, session, symbol, direction, or asset class.

### Administrative & Health
- `GET /api/v1/admin/health`: Live health report on 100,000 demo dataset integrity.
- `POST /api/v1/admin/seed`: Deterministic seed trigger.
- `POST /api/v1/admin/reset`: Safe demo data reset.

---

## 8. Synthetic Demo Data Disclosure & Limitations

1. **Synthetic Nature:** All 100,000 trade records and 10 trader profiles in this dataset are synthetically generated for demonstration, software testing, and performance validation.
2. **No Live Broker Connections:** The records do not represent real-money trading, live broker connections, or proprietary financial histories.
3. **Market Behavior Representation:** The simulated outcomes, win rates, and drawdowns are modeled behavioral personas and do not represent predictive market signals or financial advice.
