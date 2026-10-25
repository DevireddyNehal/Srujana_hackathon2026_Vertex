from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .date_ranges import PRESETS
from .db import connect
from .seed_demo import initialize_database, seed_demo_trades
from .stats import NotFound, breakdown, daily_pnl, get_account, list_accounts, overview, resolve_range

STATIC_DIR = Path(__file__).parent / "static"
SessionFilter = Literal["all", "London", "New York", "Asian", "Off-hours"]


def _require_demo_account(connection, user_id: str) -> dict:
    try:
        account = get_account(connection, user_id)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not account["is_demo"]:
        raise HTTPException(
            status_code=403,
            detail="Real accounts require an authenticated session.",
        )
    return account


def _stats_payload(analytics: dict, session: str) -> dict:
    daily = analytics["daily_pnl"]
    return {
        "user_id": analytics["account"]["user_id"],
        "range": {
            "preset": analytics["period"]["key"],
            "start": analytics["period"]["start"],
            "end": analytics["period"]["end"],
        },
        "filters": {"session": session},
        "summary": {
            "trade_count": analytics["closed_trades"],
            "winning_trades": analytics["win_rate"]["wins"],
            "losing_trades": analytics["win_rate"]["losses"],
            "breakeven_trades": analytics["win_rate"]["break_even"],
            "win_rate_pct": analytics["win_rate"]["value"],
            "net_pnl": analytics["net_pnl"],
            "average_pnl": analytics["expectancy"],
            "gross_profit": analytics["profit_factor"]["gross_profit"],
            "gross_loss": analytics["profit_factor"]["gross_loss"],
            "profit_factor": analytics["profit_factor"]["value"],
            "gross_pnl": analytics["costs"]["gross_pnl"],
            "fees": analytics["costs"]["commission"] + analytics["costs"]["fees"],
            "max_drawdown": analytics["max_drawdown"]["amount"],
        },
        "by_session": [
            {"session": item["name"], "trades": item["trades"], "net_pnl": item["net_pnl"]}
            for item in analytics["sessions"]
        ],
        "by_symbol": [
            {"symbol": item["name"], "trades": item["trades"], "net_pnl": item["net_pnl"]}
            for item in analytics["symbols"]
        ],
        "equity_curve": [
            {
                "date": item["date"],
                "daily_pnl": item["net_pnl"],
                "equity": item["cumulative_pnl"],
            }
            for item in daily["days"]
        ],
        "disclaimer": analytics["disclaimer"],
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(settings.database_path)
        if settings.seed_demo_on_startup:
            seed_demo_trades(settings.database_path, settings.demo_trade_count)
        yield

    app = FastAPI(
        title="Trading User Statistics",
        description="Closed-trade analytics from a dedicated SQLite database.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/accounts")
    def accounts() -> list[dict]:
        connection = connect(settings.database_path)
        try:
            return list_accounts(connection)
        finally:
            connection.close()

    @app.get("/api/date-ranges")
    def date_ranges(user_id: str = Query(default="demo_01", min_length=1, max_length=80)) -> dict:
        connection = connect(settings.database_path)
        try:
            account = _require_demo_account(connection, user_id)
            earliest = connection.execute(
                """SELECT MIN(closed_date) FROM trades
                   WHERE user_id = ? AND status = 'closed'""",
                (user_id,),
            ).fetchone()[0]
            return {
                "presets": list(PRESETS),
                "earliest": earliest,
                "latest": account["data_end"],
            }
        finally:
            connection.close()

    def get_analytics(
        user_id: str,
        range_key: str,
        start: str | None,
        end: str | None,
        session: str,
    ) -> dict:
        connection = connect(settings.database_path)
        try:
            _require_demo_account(connection, user_id)
            return overview(connection, user_id, range_key, start, end, session=session)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            connection.close()

    @app.get("/api/overview")
    def get_overview(
        user: str = Query(default="demo_01", min_length=1, max_length=80),
        range: str = Query(default="90d"),
        start: str | None = None,
        end: str | None = None,
        session: SessionFilter = "all",
    ) -> dict:
        return get_analytics(user, range, start, end, session)

    @app.get("/api/stats")
    def get_stats(
        user_id: str = Query(default="demo_01", min_length=1, max_length=80),
        range: str = Query(default="30d"),
        start: str | None = None,
        end: str | None = None,
        session: SessionFilter = "all",
    ) -> dict:
        return _stats_payload(get_analytics(user_id, range, start, end, session), session)

    @app.get("/api/daily-pnl")
    def get_daily_pnl(
        user: str = Query(default="demo_01", min_length=1, max_length=80),
        range: str = Query(default="90d"),
        start: str | None = None,
        end: str | None = None,
        session: SessionFilter = "all",
    ) -> dict:
        connection = connect(settings.database_path)
        try:
            account = _require_demo_account(connection, user)
            first, last = resolve_range(connection, account, range, start, end)
            return daily_pnl(connection, account, first, last, session=session)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            connection.close()

    @app.get("/api/breakdown")
    def get_breakdown(
        user: str = Query(default="demo_01", min_length=1, max_length=80),
        range: str = Query(default="90d"),
        start: str | None = None,
        end: str | None = None,
        by: Literal["setup", "session", "symbol"] = "setup",
        session: SessionFilter = "all",
    ) -> list[dict]:
        connection = connect(settings.database_path)
        try:
            account = _require_demo_account(connection, user)
            first, last = resolve_range(connection, account, range, start, end)
            return breakdown(connection, account, first, last, by, session=session)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            connection.close()

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
