import calendar as calendar_mod
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import database, schemas
from ..services import pnl as pnl_service
from ..services.csv_export import rows_to_csv

router = APIRouter(prefix="/api/pnl", tags=["pnl"])


@router.get("/calendar", response_model=list[schemas.DayPnl])
def calendar_pnl(
    year: int = Query(..., ge=1990, le=3000),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(database.get_db),
):
    start = date(year, month, 1)
    last_day = calendar_mod.monthrange(year, month)[1]
    end = date(year, month, last_day)
    rows = pnl_service.daily_pnl(db, start=start, end=end)
    return [
        schemas.DayPnl(date=row.period, pnl=round(row.pnl, 2), trade_count=row.trade_count)
        for row in rows
    ]


@router.get("/aggregate", response_model=list[schemas.PeriodPnl])
def aggregate_pnl(
    period: Literal["day", "week", "month"] = "day",
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(database.get_db),
):
    rows = pnl_service.aggregate_pnl(db, period=period, start=start, end=end)
    return [
        schemas.PeriodPnl(period=row.period, pnl=round(row.pnl, 2), trade_count=row.trade_count)
        for row in rows
    ]


@router.get("/summary", response_model=schemas.Summary)
def get_summary(db: Session = Depends(database.get_db)):
    return pnl_service.summary(db)


@router.get("/equity-curve", response_model=list[schemas.EquityPoint])
def equity_curve(
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(database.get_db),
):
    return pnl_service.equity_curve(db, start=start, end=end)


@router.get("/export")
def export_daily_pnl(
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(database.get_db),
):
    rows = pnl_service.daily_pnl(db, start=start, end=end)
    csv_rows = [{"date": row.period, "pnl": round(row.pnl, 2), "trade_count": row.trade_count} for row in rows]
    csv_body = rows_to_csv(["date", "pnl", "trade_count"], csv_rows)
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="daily_pnl.csv"'},
    )
