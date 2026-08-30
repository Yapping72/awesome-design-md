"""Open-position (unrealized P&L) computation from imported executions.

IBKR's own Realized P/L (used elsewhere in this app) only covers closed
fills, so it says nothing about positions still open. To value those we
need a cost basis, which this module tracks with a running weighted-average
cost per symbol (not FIFO) — a standard, simple approximation: adding to a
position blends into the average cost, reducing it leaves the average cost
unchanged, and flipping through zero resets the cost basis to the fill that
caused the flip.
"""

from collections import OrderedDict
from typing import TypedDict

from sqlalchemy.orm import Session

from .. import models


class OpenPosition(TypedDict):
    symbol: str
    quantity: float
    avg_cost: float
    currency: str | None
    asset_category: str | None


def compute_open_positions(db: Session) -> list[OpenPosition]:
    executions = (
        db.query(models.Execution)
        .order_by(models.Execution.symbol, models.Execution.trade_datetime)
        .all()
    )

    state: "OrderedDict[str, dict]" = OrderedDict()

    for execution in executions:
        s = state.setdefault(
            execution.symbol,
            {
                "qty": 0.0,
                "avg_cost": 0.0,
                "currency": execution.currency,
                "asset_category": execution.asset_category,
            },
        )
        qty = s["qty"]
        trade_qty = execution.quantity
        trade_price = execution.price
        new_qty = qty + trade_qty

        same_direction_or_opening = qty == 0 or (qty > 0) == (trade_qty > 0)
        if same_direction_or_opening:
            s["avg_cost"] = (
                trade_price
                if qty == 0
                else (s["avg_cost"] * qty + trade_price * trade_qty) / new_qty
            )
        elif (qty > 0 > new_qty) or (qty < 0 < new_qty):
            # Reduced through zero and flipped direction: cost basis resets
            # to the price of the fill that caused the flip.
            s["avg_cost"] = trade_price
        # else: pure reduction, average cost of the remaining shares is unchanged

        s["qty"] = new_qty

    positions: list[OpenPosition] = []
    for symbol, s in state.items():
        if abs(s["qty"]) > 1e-9:
            positions.append(
                OpenPosition(
                    symbol=symbol,
                    quantity=round(s["qty"], 6),
                    avg_cost=round(s["avg_cost"], 4),
                    currency=s["currency"],
                    asset_category=s["asset_category"],
                )
            )
    return positions
