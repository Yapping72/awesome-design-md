from datetime import date
from typing import Optional

from sqlalchemy import Float, cast, func
from sqlalchemy.orm import Session

from .. import models

# Net P/L per fill = IBKR's realized P/L (only non-zero on closing fills)
# plus commission (stored as a negative number by IBKR).
NET_PNL_EXPR = cast(
    func.coalesce(models.Execution.realized_pnl, 0)
    + func.coalesce(models.Execution.commission, 0),
    Float,
)

_PERIOD_TRUNC = {"day": "day", "week": "week", "month": "month"}


def daily_pnl(db: Session, start: Optional[date] = None, end: Optional[date] = None):
    q = db.query(
        models.Execution.trade_date.label("period"),
        func.sum(NET_PNL_EXPR).label("pnl"),
        func.count(models.Execution.id).label("trade_count"),
    ).group_by(models.Execution.trade_date)

    if start:
        q = q.filter(models.Execution.trade_date >= start)
    if end:
        q = q.filter(models.Execution.trade_date <= end)

    return q.order_by(models.Execution.trade_date).all()


def aggregate_pnl(
    db: Session,
    period: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
):
    if period not in _PERIOD_TRUNC:
        raise ValueError(f"invalid period: {period}")

    trunc = func.date_trunc(_PERIOD_TRUNC[period], models.Execution.trade_datetime)
    q = db.query(
        cast(trunc, models.Execution.trade_date.type).label("period"),
        func.sum(NET_PNL_EXPR).label("pnl"),
        func.count(models.Execution.id).label("trade_count"),
    ).group_by(trunc)

    if start:
        q = q.filter(models.Execution.trade_datetime >= start)
    if end:
        q = q.filter(models.Execution.trade_datetime <= end)

    return q.order_by(trunc).all()


def equity_curve(db: Session, start: Optional[date] = None, end: Optional[date] = None):
    """Cumulative realized P&L over time, one point per day that had a fill.

    A running sum over daily_pnl rather than a SQL window function — the
    row count here is bounded by trading days, not fills, so there's no
    real cost to doing it in Python, and it keeps the query portable.
    """
    running_total = 0.0
    points = []
    for row in daily_pnl(db, start=start, end=end):
        running_total += row.pnl
        points.append({"date": row.period, "pnl": round(row.pnl, 2), "cumulative_pnl": round(running_total, 2)})
    return points


def summary(db: Session) -> dict:
    total_trades = db.query(func.count(models.Execution.id)).scalar() or 0
    total_pnl = db.query(func.sum(NET_PNL_EXPR)).scalar() or 0.0

    # "Closing" fills are the ones IBKR attached a non-zero realized P/L to;
    # win/loss stats are only meaningful on those (an opening fill has no
    # outcome yet).
    closing_rows = (
        db.query(NET_PNL_EXPR.label("pnl"))
        .filter(models.Execution.realized_pnl != 0)
        .all()
    )
    closing_pnls = [row.pnl for row in closing_rows]
    wins = [p for p in closing_pnls if p > 0]
    losses = [p for p in closing_pnls if p < 0]

    win_rate = (len(wins) / len(closing_pnls) * 100) if closing_pnls else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss else None

    day_rows = daily_pnl(db)
    best_day = max(day_rows, key=lambda r: r.pnl, default=None)
    worst_day = min(day_rows, key=lambda r: r.pnl, default=None)

    return {
        "total_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "closing_trades": len(closing_pnls),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "best_day": {
            "date": best_day.period,
            "pnl": round(best_day.pnl, 2),
            "trade_count": best_day.trade_count,
        }
        if best_day
        else None,
        "worst_day": {
            "date": worst_day.period,
            "pnl": round(worst_day.pnl, 2),
            "trade_count": worst_day.trade_count,
        }
        if worst_day
        else None,
    }
