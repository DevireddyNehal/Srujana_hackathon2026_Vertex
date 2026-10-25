# Trading User Statistics

An isolated FastAPI + SQLite dashboard for closed-trade performance, daily P&L, trading setups, and market-session statistics. It is separate from the portfolio stress-test API and uses its own SQLite database.

## Run

From the repository root:

```powershell
python -m pip install -r backend/trading_user_stats/requirements.txt
python -m uvicorn trading_user_stats.app.api:app --app-dir backend --reload --port 8001
```

Open `http://127.0.0.1:8001/` for the dashboard or `/docs` for the API schema.

On first startup, the app initializes SQLite and seeds 100,000 deterministic demo trades across ten synthetic accounts. Seeding replaces only the app's own demo rows and refuses to modify a real account. Use `TRADING_STATS_DEMO_TRADE_COUNT` to choose a different seed size, `TRADING_STATS_SEED_DEMO=false` to disable seeding, and `TRADING_STATS_DB_PATH` to change the database location. Demo seeding is disabled when `APP_ENV=production`.

## API

- `GET /api/health`
- `GET /api/accounts`
- `GET /api/date-ranges?user_id=demo_01`
- `GET /api/overview?user=demo_01&range=30d`
- `GET /api/stats?user_id=demo_01&range=30d&session=all`
- `GET /api/daily-pnl?user=demo_01&range=30d`
- `GET /api/breakdown?user=demo_01&range=30d&by=setup`

Date ranges are `7d`, `30d`, `90d`, `ytd`, `1y`, `all`, and `custom`. Custom ranges require inclusive ISO dates: `range=custom&start=2026-01-01&end=2026-01-31`, and are limited to 3,700 days. Session filters are `all`, `London`, `New York`, `Asian`, and `Off-hours`; market hours use DST-aware local time zones. Trades are grouped by closing date in each account's time zone. The API intentionally serves demo accounts only; real accounts require integration with an authenticated, server-verified identity.

The demo dataset uses a seeded synthetic trade model; results are illustrative and are not forecasts or investment advice. Net P&L is gross P&L less commission, fees, and slippage, plus signed swap. Profit factor uses positive versus negative **net** trade P&L. Max drawdown is measured on the realized closed-trade equity curve and excludes intratrade moves. Open trades are excluded from realized statistics.

## Tests

```powershell
python -m pip install -r backend/trading_user_stats/requirements-dev.txt
python -m pytest backend/trading_user_stats/tests -q
```
