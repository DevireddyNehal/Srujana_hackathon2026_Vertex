"""
TradeFXBook FastAPI Application and Router Endpoints.
Provides RESTful APIs for Trade Journal management, High-Performance Analytics,
Demo Trader Switching, and CSV Exports with strict user isolation.
"""

from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from tradefxbook.config import settings
from tradefxbook.database import init_db
from tradefxbook.models import (
    TradeCreate,
    TradeUpdate,
    TradeOut,
    PaginatedTrades,
    PerformanceMetrics,
    DailyPnLPoint,
    BreakdownItem,
    DemoHealthReport,
    UserOut,
)
from tradefxbook.repository import (
    get_user_by_id,
    list_users,
    get_trade_by_id,
    create_trade,
    update_trade,
    delete_trade,
    list_trades_paginated,
    export_trades_to_csv,
    get_user_closed_trades,
    get_analytics_breakdown,
    compute_user_analytics_db,
)
from tradefxbook.calculations import (
    compute_aggregate_metrics,
    generate_daily_pnl_series,
)
from tradefxbook.generator import (
    check_demo_dataset_status,
    seed_demo_dataset,
    reset_demo_data,
)
from tradefxbook.auth import get_current_user


router = APIRouter(prefix="/api/v1")


# ==========================================
# AUTHENTICATION & DEMO TRADER SWITCHER
# ==========================================

@router.get("/auth/me", response_model=UserOut)
def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns currently authenticated user profile and starting balance."""
    return current_user


@router.get("/auth/demo-users", response_model=List[UserOut])
def get_demo_users():
    """Lists the 10 seeded demo traders with their styles and configurations."""
    return list_users(is_demo_only=True)


@router.post("/auth/switch-demo/{user_id}")
def switch_active_demo_user(user_id: str):
    """
    Switches active demo user context.
    Returns session confirmation and token for the selected demo trader.
    """
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    if not user.get("is_demo"):
        raise HTTPException(status_code=400, detail="Only demo users can be switched via this endpoint.")

    return {
        "status": "SUCCESS",
        "active_user_id": user["id"],
        "user_name": user["name"],
        "token": f"demo_token_{user['id']}",
        "message": f"Successfully switched to {user['name']}.",
    }


# ==========================================
# TRADE JOURNAL MANAGEMENT
# ==========================================

@router.get("/trades", response_model=PaginatedTrades)
def list_trades(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO)"),
    symbol: Optional[str] = Query(None),
    direction: Optional[str] = Query(None, pattern="^(LONG|SHORT|long|short)$"),
    status: Optional[str] = Query(None, pattern="^(OPEN|CLOSED|open|closed)$"),
    outcome: Optional[str] = Query(None, pattern="^(WIN|LOSS|BREAKEVEN|win|loss|breakeven)$"),
    strategy: Optional[str] = Query(None),
    session: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search symbol, notes, or tags"),
    sort_by: str = Query("exit_time", pattern="^(entry_time|exit_time|net_pnl|gross_pnl|symbol|quantity|realized_r_multiple)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc|ASC|DESC)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List trades with database-level pagination, sorting, and multi-field filtering.
    Strictly isolated: returns only the current user's trades.
    """
    result = list_trades_paginated(
        user_id=current_user["id"],
        date_from=date_from,
        date_to=date_to,
        symbol=symbol,
        direction=direction,
        status=status,
        outcome=outcome,
        strategy=strategy,
        session=session,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return result


@router.post("/trades", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def create_new_trade(
    trade_in: TradeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Creates a new journal trade entry.
    Calculates gross P&L, commissions, fees, signed swap, and net realized P&L authoritatively.
    """
    trade_dict = trade_in.model_dump()
    created = create_trade(user_id=current_user["id"], trade_data=trade_dict)
    return created


@router.get("/trades/{trade_id}", response_model=TradeOut)
def get_trade_details(
    trade_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Retrieves full details of an individual trade.
    Enforces ownership: returns 404 if not found or belongs to another user.
    """
    trade = get_trade_by_id(trade_id=trade_id, user_id=current_user["id"])
    if not trade:
        raise HTTPException(
            status_code=404,
            detail=f"Trade {trade_id} not found or you do not have permission to view it.",
        )
    return trade


@router.put("/trades/{trade_id}", response_model=TradeOut)
def update_trade_details(
    trade_id: str,
    update_in: TradeUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Updates an existing trade and recalculates dependent financial fields.
    Enforces ownership: returns 404 if not found or unauthorized.
    """
    update_data = update_in.model_dump(exclude_unset=True)
    try:
        updated = update_trade(
            trade_id=trade_id,
            user_id=current_user["id"],
            update_data=update_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Trade {trade_id} not found or you do not have permission to modify it.",
        )
    return updated


@router.delete("/trades/{trade_id}")
def delete_trade_record(
    trade_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Deletes a trade record.
    Enforces ownership: returns 404 if not found or unauthorized.
    """
    success = delete_trade(trade_id=trade_id, user_id=current_user["id"])
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Trade {trade_id} not found or you do not have permission to delete it.",
        )
    return {"status": "SUCCESS", "message": f"Trade {trade_id} successfully deleted."}


@router.get("/trades/export/csv")
def export_trades_csv(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    session: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Exports filtered trade history to CSV.
    Guarantees user isolation: never contains another user's trades.
    """
    csv_content = export_trades_to_csv(
        user_id=current_user["id"],
        date_from=date_from,
        date_to=date_to,
        symbol=symbol,
        direction=direction,
        status=status,
        outcome=outcome,
        strategy=strategy,
        session=session,
        search=search,
    )
    filename = f"trades_{current_user['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ==========================================
# TRADING ANALYTICS & STATISTICS
# ==========================================

def _resolve_date_range(
    range_preset: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    user_tz: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolves date presets (7d, 30d, 90d, ytd, 1y, all) into calendar boundaries."""
    if not range_preset or range_preset.lower() == "custom":
        return date_from, date_to

    preset = range_preset.lower()
    ref_dt = datetime.fromisoformat(settings.REFERENCE_END_DATE.replace("Z", "+00:00"))
    ref_date = ref_dt.date()

    if preset == "7d":
        start_d = ref_date - timedelta(days=7)
        return start_d.isoformat(), ref_date.isoformat()
    elif preset == "30d":
        start_d = ref_date - timedelta(days=30)
        return start_d.isoformat(), ref_date.isoformat()
    elif preset == "90d":
        start_d = ref_date - timedelta(days=90)
        return start_d.isoformat(), ref_date.isoformat()
    elif preset == "ytd":
        start_d = date(ref_date.year, 1, 1)
        return start_d.isoformat(), ref_date.isoformat()
    elif preset == "1y":
        start_d = ref_date - timedelta(days=365)
        return start_d.isoformat(), ref_date.isoformat()
    elif preset == "all":
        return None, None
    return date_from, date_to


@router.get("/analytics/overview", response_model=PerformanceMetrics)
def get_analytics_overview(
    range_preset: Optional[str] = Query("all", description="7d, 30d, 90d, ytd, 1y, all, custom"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    session: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Computes all 22 required trading performance metrics + secondary statistics
    authoritatively strictly from the current user's closed trades.
    """
    resolved_from, resolved_to = _resolve_date_range(
        range_preset, date_from, date_to, current_user.get("timezone", "UTC")
    )

    metrics = compute_user_analytics_db(
        user_id=current_user["id"],
        starting_balance=current_user.get("starting_balance", 50000.0),
        user_name=current_user["name"],
        account_currency=current_user.get("currency", "USD"),
        timezone_str=current_user.get("timezone", "UTC"),
        date_from=resolved_from,
        date_to=resolved_to,
        symbol=symbol,
        strategy=strategy,
        session=session,
        direction=direction,
        outcome=outcome,
    )

    return metrics


@router.get("/analytics/daily-pnl", response_model=List[DailyPnLPoint])
def get_daily_pnl(
    range_preset: Optional[str] = Query("30d", description="7d, 30d, 90d, ytd, 1y, all, custom"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Daily net realized P&L and cumulative curve.
    Returns EVERY calendar day in the requested range (including weekends/zero days).
    Reconciles exactly with total closed trade net P&L.
    """
    resolved_from, resolved_to = _resolve_date_range(
        range_preset, date_from, date_to, current_user.get("timezone", "UTC")
    )

    if resolved_from and resolved_to:
        d_start = (date.fromisoformat(resolved_from) - timedelta(days=2)).isoformat()
        d_end = (date.fromisoformat(resolved_to) + timedelta(days=2)).isoformat()
        trades = get_user_closed_trades(user_id=current_user["id"], date_from=d_start, date_to=d_end)
    else:
        trades = get_user_closed_trades(user_id=current_user["id"])
        if trades:
            resolved_from = trades[0]["exit_time"][:10]
            resolved_to = trades[-1]["exit_time"][:10]

    if not resolved_from or not resolved_to:
        return []

    series = generate_daily_pnl_series(
        trades=trades,
        start_date=resolved_from,
        end_date=resolved_to,
        timezone_str=current_user.get("timezone", "UTC"),
    )
    return series


@router.get("/analytics/equity-curve")
def get_equity_curve(
    range_preset: Optional[str] = Query("all"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Realized equity curve and peak-to-trough drawdown progression.
    """
    resolved_from, resolved_to = _resolve_date_range(
        range_preset, date_from, date_to, current_user.get("timezone", "UTC")
    )

    trades = get_user_closed_trades(
        user_id=current_user["id"],
        date_from=resolved_from,
        date_to=resolved_to,
    )

    starting_balance = float(current_user.get("starting_balance", 50000.0))
    equity = starting_balance
    hwm = starting_balance

    points = [
        {
            "trade_id": None,
            "timestamp": trades[0]["entry_time"] if trades else "START",
            "realized_pnl": 0.0,
            "equity": equity,
            "high_water_mark": hwm,
            "drawdown_currency": 0.0,
            "drawdown_pct": 0.0,
        }
    ]

    for t in trades:
        net = round(float(t.get("net_pnl", 0.0)), 2)
        equity = round(equity + net, 2)
        if equity > hwm:
            hwm = equity
        dd_curr = round(hwm - equity, 2)
        dd_pct = round((dd_curr / hwm) * 100.0, 2) if hwm > 0 else 0.0

        points.append(
            {
                "trade_id": t["id"],
                "timestamp": t["exit_time"],
                "realized_pnl": net,
                "equity": equity,
                "high_water_mark": hwm,
                "drawdown_currency": dd_curr,
                "drawdown_pct": dd_pct,
            }
        )

    return {
        "user_id": current_user["id"],
        "starting_balance": starting_balance,
        "current_equity": equity,
        "peak_equity": hwm,
        "points": points,
    }


@router.get("/analytics/breakdown", response_model=List[BreakdownItem])
def get_breakdowns(
    group_by: str = Query("strategy", pattern="^(strategy|session|symbol|direction|asset_class)$"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Performance breakdowns grouped by strategy, session, symbol, direction, or asset class.
    """
    return get_analytics_breakdown(
        user_id=current_user["id"],
        group_by_field=group_by,
        date_from=date_from,
        date_to=date_to,
    )


# ==========================================
# ADMIN & DEMO MAINTENANCE
# ==========================================

@router.get("/admin/health", response_model=DemoHealthReport)
def get_demo_health():
    """
    Health check verifying the demo dataset integrity:
    10 demo users, exactly 10,000 closed trades per user, 100,000 total.
    """
    status_info = check_demo_dataset_status()
    demo_users_count = status_info["demo_users_count"]
    trades_per_user = status_info["trades_per_user"]
    total_trades = status_info["demo_trades_count"]
    closed_trades = status_info["closed_demo_trades_count"]

    checks = {
        "has_exact_10_users": demo_users_count == 10,
        "has_exact_100k_trades": total_trades == 100000,
        "has_exact_100k_closed_trades": closed_trades == 100000,
        "all_users_have_10k_trades": (
            len(trades_per_user) == 10 and all(cnt == 10000 for cnt in trades_per_user.values())
        ),
        "seed_batch_matches": status_info["seed_batch"] == settings.DEMO_SEED_BATCH,
    }

    return {
        "total_demo_users": demo_users_count,
        "trades_per_user": trades_per_user,
        "total_seeded_trades": total_trades,
        "total_closed_seeded_trades": closed_trades,
        "seed_batch": settings.DEMO_SEED_BATCH,
        "is_healthy": all(checks.values()),
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/admin/seed")
def seed_dataset(force: bool = False):
    """Seeds the demo dataset deterministically."""
    result = seed_demo_dataset(force_reseed=force)
    return result


@router.post("/admin/reset")
def reset_dataset(confirm: bool = Query(False)):
    """Safely resets demo records without touching non-demo data."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must specify confirm=true to perform a demo dataset reset.",
        )
    return reset_demo_data()


# ==========================================
# FASTAPI APPLICATION BUILDER
# ==========================================

def create_app() -> FastAPI:
    """Factory creating configured TradeFXBook FastAPI instance."""
    app = FastAPI(
        title="TradeFXBook Journal & Analytics API",
        version="1.0.0",
        description="High-performance Trading Journal and Analytics platform with 100,000 seeded trades across 10 isolated demo users.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize schema
    init_db()

    # Include REST API routes
    app.include_router(router)

    # Serve static UI
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", response_class=HTMLResponse)
        @app.get("/journal", response_class=HTMLResponse)
        def serve_ui():
            index_path = static_dir / "index.html"
            if index_path.exists():
                return HTMLResponse(content=index_path.read_text(), status_code=200)
            return HTMLResponse("<h1>TradeFXBook UI Loading...</h1>")

    return app


app = create_app()
