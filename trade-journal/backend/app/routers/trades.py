from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..services.round_trips import compute_round_trips

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("/round-trips", response_model=schemas.RoundTripsPage)
def list_round_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    symbol: Optional[str] = None,
    db: Session = Depends(database.get_db),
):
    round_trips = compute_round_trips(db)
    if symbol:
        needle = symbol.lower()
        round_trips = [rt for rt in round_trips if needle in rt["symbol"].lower()]

    # Most recent exit first, matching the raw-fills blotter's ordering.
    round_trips.sort(key=lambda rt: rt["exit_time"], reverse=True)

    total = len(round_trips)
    start_idx = (page - 1) * page_size
    page_items = round_trips[start_idx : start_idx + page_size]

    return schemas.RoundTripsPage(
        total=total,
        page=page,
        page_size=page_size,
        items=[schemas.RoundTripOut(**rt) for rt in page_items],
    )


@router.get("", response_model=schemas.TradesPage)
def list_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    symbol: Optional[str] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(database.get_db),
):
    q = db.query(models.Execution)
    if symbol:
        q = q.filter(models.Execution.symbol.ilike(f"%{symbol}%"))
    if start:
        q = q.filter(models.Execution.trade_date >= start)
    if end:
        q = q.filter(models.Execution.trade_date <= end)

    total = q.with_entities(func.count(models.Execution.id)).scalar() or 0

    rows = (
        q.order_by(models.Execution.trade_datetime.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        schemas.TradeOut(
            id=row.id,
            symbol=row.symbol,
            asset_category=row.asset_category,
            currency=row.currency,
            trade_datetime=row.trade_datetime,
            trade_date=row.trade_date,
            quantity=row.quantity,
            price=row.price,
            proceeds=row.proceeds,
            commission=row.commission,
            realized_pnl=row.realized_pnl,
            net_pnl=round((row.realized_pnl or 0) + (row.commission or 0), 2),
            code=row.code,
        )
        for row in rows
    ]

    return schemas.TradesPage(total=total, page=page, page_size=page_size, items=items)


@router.delete("")
def clear_trades(db: Session = Depends(database.get_db)):
    deleted = db.query(models.Execution).delete()
    db.commit()
    return {"deleted": deleted}
