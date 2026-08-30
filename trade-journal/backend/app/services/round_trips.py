"""Pairs opening and closing fills into discrete "round trip" trades.

Most trade journals present history as a list of trades — one entry, one
exit — rather than a raw list of fills. IBKR's own Realized P/L is per
*closing fill*, not per round trip, and a single closing fill can close
across several earlier opening fills (partial fills, scaling in/out). To
get a clean entry->exit list we FIFO-match fills per symbol ourselves,
splitting both commission and P&L proportionally across whatever lots a
closing fill consumes.

This intentionally does not reuse IBKR's `realized_pnl` field: splitting
one closing fill across multiple FIFO lots means recomputing P&L from the
entry/exit price difference is the only way to get a correct number per
round trip. It should match IBKR's total for a fully-closed position (same
inputs, same arithmetic), just broken down differently.
"""

from collections import deque
from datetime import datetime
from typing import TypedDict

from sqlalchemy.orm import Session

from .. import models


class RoundTrip(TypedDict):
    round_trip_id: str
    symbol: str
    side: str  # "long" | "short"
    quantity: float
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    commission: float
    realized_pnl: float
    hold_seconds: float


class _Lot:
    __slots__ = ("qty", "price", "time", "commission_per_share", "execution_id")

    def __init__(
        self,
        qty: float,
        price: float,
        time: datetime,
        commission_per_share: float,
        execution_id: int,
    ):
        self.qty = qty
        self.price = price
        self.time = time
        self.commission_per_share = commission_per_share
        self.execution_id = execution_id


def compute_round_trips(db: Session) -> list[RoundTrip]:
    executions = (
        db.query(models.Execution)
        .order_by(models.Execution.symbol, models.Execution.trade_datetime, models.Execution.id)
        .all()
    )

    queues: dict[str, deque[_Lot]] = {}
    round_trips: list[RoundTrip] = []

    for execution in executions:
        queue = queues.setdefault(execution.symbol, deque())
        remaining_qty = execution.quantity
        commission_per_share = (
            (execution.commission or 0) / abs(execution.quantity) if execution.quantity else 0.0
        )

        while remaining_qty != 0:
            opens_new_lot = not queue or (queue[0].qty > 0) == (remaining_qty > 0)
            if opens_new_lot:
                queue.append(
                    _Lot(
                        remaining_qty,
                        execution.price,
                        execution.trade_datetime,
                        commission_per_share,
                        execution.id,
                    )
                )
                remaining_qty = 0
                continue

            lot = queue[0]
            close_qty = min(abs(lot.qty), abs(remaining_qty))
            side = "long" if lot.qty > 0 else "short"

            price_delta = execution.price - lot.price
            gross_pnl = price_delta * close_qty if side == "long" else -price_delta * close_qty
            commission = lot.commission_per_share * close_qty + commission_per_share * close_qty

            round_trips.append(
                RoundTrip(
                    round_trip_id=f"{lot.execution_id}:{execution.id}",
                    symbol=execution.symbol,
                    side=side,
                    quantity=close_qty,
                    entry_time=lot.time,
                    exit_time=execution.trade_datetime,
                    entry_price=lot.price,
                    exit_price=execution.price,
                    commission=round(commission, 2),
                    realized_pnl=round(gross_pnl + commission, 2),
                    hold_seconds=(execution.trade_datetime - lot.time).total_seconds(),
                )
            )

            lot.qty -= close_qty if lot.qty > 0 else -close_qty
            remaining_qty -= close_qty if remaining_qty > 0 else -close_qty
            if lot.qty == 0:
                queue.popleft()

    round_trips.sort(key=lambda rt: rt["exit_time"])
    return round_trips
