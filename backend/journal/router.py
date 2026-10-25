from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from . import analytics, storage
from .ai_provider import review_trade
from .identity import get_current_user_id
from .schemas import TradeCreate, TradeUpdate

router = APIRouter(prefix="/api/journal", tags=["trading journal"])


@router.post("/trades", status_code=201)
def create_journal_trade(
    request: TradeCreate,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    return storage.create_trade(user_id, request)


@router.get("/trades")
def get_journal_trades(
    status: Literal["all", "open", "closed"] = "all",
    symbol: str | None = Query(default=None, min_length=1, max_length=24),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    trades, total = storage.list_trades(
        user_id, limit=limit, offset=offset, status=status, symbol=symbol
    )
    return {"trades": trades, "total": total, "limit": limit, "offset": offset}


@router.get("/trades/{trade_id}")
def get_journal_trade(trade_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    trade = storage.get_trade(user_id, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found.")
    return trade


@router.patch("/trades/{trade_id}")
def update_journal_trade(
    trade_id: str,
    request: TradeUpdate,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        trade = storage.update_trade(user_id, trade_id, request.model_dump(exclude_unset=True))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found.")
    return trade


@router.delete("/trades/{trade_id}", status_code=204)
def delete_journal_trade(
    trade_id: str,
    user_id: str = Depends(get_current_user_id),
) -> Response:
    if not storage.delete_trade(user_id, trade_id):
        raise HTTPException(status_code=404, detail="Trade not found.")
    return Response(status_code=204)


@router.get("/analytics")
def get_journal_analytics(user_id: str = Depends(get_current_user_id)) -> dict:
    return analytics.analyze_trades(storage.list_closed_trades(user_id))


@router.post("/trades/{trade_id}/review")
def get_trade_review(trade_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    trade = storage.get_trade(user_id, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found.")
    return review_trade(trade)
