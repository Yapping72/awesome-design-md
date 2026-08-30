from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..services.csv_export import rows_to_csv
from ..services.pnl import NET_PNL_EXPR
from ..services.round_trips import aggregate_by_symbol, compute_round_trips

router = APIRouter(prefix="/api/trades", tags=["trades"])

FillSortBy = Literal[
    "trade_datetime", "symbol", "quantity", "price", "commission", "realized_pnl", "net_pnl"
]
RoundTripSortBy = Literal[
    "symbol", "side", "quantity", "entry_time", "exit_time",
    "entry_price", "exit_price", "commission", "realized_pnl", "hold_seconds",
]
SortDir = Literal["asc", "desc"]

_FILL_SORT_COLUMNS = {
    "trade_datetime": models.Execution.trade_datetime,
    "symbol": models.Execution.symbol,
    "quantity": models.Execution.quantity,
    "price": models.Execution.price,
    "commission": models.Execution.commission,
    "realized_pnl": models.Execution.realized_pnl,
    "net_pnl": NET_PNL_EXPR,
}


def _csv_response(csv_body: str, filename: str) -> Response:
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _note_to_out(note: Optional[models.TradeNote]) -> tuple[Optional[str], list[str]]:
    if note is None:
        return None, []
    tags = [t for t in (note.tags or "").split(",") if t]
    return note.notes, tags


@router.get("/round-trips", response_model=schemas.RoundTripsPage)
def list_round_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    symbol: Optional[str] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    sort_by: RoundTripSortBy = "exit_time",
    sort_dir: SortDir = "desc",
    db: Session = Depends(database.get_db),
):
    round_trips = compute_round_trips(db)
    if symbol:
        needle = symbol.lower()
        round_trips = [rt for rt in round_trips if needle in rt["symbol"].lower()]
    if start:
        round_trips = [rt for rt in round_trips if rt["exit_time"].date() >= start]
    if end:
        round_trips = [rt for rt in round_trips if rt["exit_time"].date() <= end]

    round_trips.sort(key=lambda rt: rt[sort_by], reverse=(sort_dir == "desc"))

    total = len(round_trips)
    start_idx = (page - 1) * page_size
    page_items = round_trips[start_idx : start_idx + page_size]

    notes_by_id = {note.round_trip_id: note for note in db.query(models.TradeNote).all()}
    items = []
    for rt in page_items:
        notes, tags = _note_to_out(notes_by_id.get(rt["round_trip_id"]))
        items.append(schemas.RoundTripOut(**rt, notes=notes, tags=tags))

    return schemas.RoundTripsPage(total=total, page=page, page_size=page_size, items=items)


@router.get("/by-symbol", response_model=list[schemas.SymbolPerformanceOut])
def symbol_performance(db: Session = Depends(database.get_db)):
    return aggregate_by_symbol(compute_round_trips(db))


@router.get("/round-trips/export")
def export_round_trips(symbol: Optional[str] = None, db: Session = Depends(database.get_db)):
    round_trips = compute_round_trips(db)
    if symbol:
        needle = symbol.lower()
        round_trips = [rt for rt in round_trips if needle in rt["symbol"].lower()]
    round_trips.sort(key=lambda rt: rt["exit_time"], reverse=True)

    notes_by_id = {note.round_trip_id: note for note in db.query(models.TradeNote).all()}
    rows = []
    for rt in round_trips:
        notes, tags = _note_to_out(notes_by_id.get(rt["round_trip_id"]))
        rows.append({**rt, "notes": notes or "", "tags": "|".join(tags)})

    csv_body = rows_to_csv(
        [
            "symbol", "side", "quantity", "entry_time", "exit_time", "entry_price",
            "exit_price", "commission", "realized_pnl", "hold_seconds", "tags", "notes",
        ],
        rows,
    )
    return _csv_response(csv_body, "round_trips.csv")


@router.put("/round-trips/{round_trip_id}/notes", response_model=schemas.TradeNoteOut)
def upsert_round_trip_notes(
    round_trip_id: str,
    payload: schemas.TradeNoteIn,
    db: Session = Depends(database.get_db),
):
    note = (
        db.query(models.TradeNote)
        .filter(models.TradeNote.round_trip_id == round_trip_id)
        .first()
    )
    notes_text = payload.notes.strip() if payload.notes and payload.notes.strip() else None
    tags_csv = ",".join(t.strip() for t in payload.tags if t.strip()) or None

    if note is None:
        note = models.TradeNote(round_trip_id=round_trip_id, notes=notes_text, tags=tags_csv)
        db.add(note)
    else:
        note.notes = notes_text
        note.tags = tags_csv

    db.commit()

    notes, tags = _note_to_out(note)
    return schemas.TradeNoteOut(round_trip_id=round_trip_id, notes=notes, tags=tags)


@router.get("/export")
def export_trades(
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
    rows = q.order_by(models.Execution.trade_datetime.desc()).all()

    csv_rows = [
        {
            "trade_datetime": row.trade_datetime,
            "symbol": row.symbol,
            "asset_category": row.asset_category,
            "currency": row.currency,
            "quantity": row.quantity,
            "price": row.price,
            "proceeds": row.proceeds,
            "commission": row.commission,
            "realized_pnl": row.realized_pnl,
            "net_pnl": round((row.realized_pnl or 0) + (row.commission or 0), 2),
            "code": row.code,
        }
        for row in rows
    ]
    csv_body = rows_to_csv(
        [
            "trade_datetime", "symbol", "asset_category", "currency", "quantity", "price",
            "proceeds", "commission", "realized_pnl", "net_pnl", "code",
        ],
        csv_rows,
    )
    return _csv_response(csv_body, "trade_fills.csv")


@router.get("", response_model=schemas.TradesPage)
def list_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    symbol: Optional[str] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    sort_by: FillSortBy = "trade_datetime",
    sort_dir: SortDir = "desc",
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

    column = _FILL_SORT_COLUMNS[sort_by]
    order = column.asc() if sort_dir == "asc" else column.desc()
    rows = q.order_by(order).offset((page - 1) * page_size).limit(page_size).all()

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
    db.query(models.UploadBatch).delete()
    db.commit()
    return {"deleted": deleted}
