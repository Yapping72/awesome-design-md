from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import database, schemas
from ..services import market_data
from ..services import positions as positions_service

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/fx/usdsgd", response_model=schemas.FxRate)
def usd_sgd_rate():
    # Endpoints are plain `def`s (not async) so FastAPI runs the blocking
    # yfinance network call in its threadpool instead of on the event loop.
    return schemas.FxRate(pair="USDSGD", rate=market_data.get_fx_rate("USDSGD"))


@router.get("/portfolio", response_model=schemas.Portfolio)
def portfolio(db: Session = Depends(database.get_db)):
    open_positions = positions_service.compute_open_positions(db)
    quotes = market_data.get_quotes([p["symbol"] for p in open_positions])
    usd_sgd = market_data.get_fx_rate("USDSGD")

    enriched: list[schemas.Position] = []
    total_market_value_usd = 0.0
    total_unrealized_pnl_usd = 0.0

    for p in open_positions:
        last_price = quotes.get(p["symbol"])
        market_value = last_price * p["quantity"] if last_price is not None else None
        unrealized_pnl = (
            (last_price - p["avg_cost"]) * p["quantity"] if last_price is not None else None
        )

        # Only USD-denominated positions feed the SGD-converted totals below;
        # this app is built around IBKR US-brokerage exports where equities
        # are almost always quoted in USD.
        if p["currency"] in (None, "USD"):
            if market_value is not None:
                total_market_value_usd += market_value
            if unrealized_pnl is not None:
                total_unrealized_pnl_usd += unrealized_pnl

        enriched.append(
            schemas.Position(
                symbol=p["symbol"],
                quantity=p["quantity"],
                avg_cost=p["avg_cost"],
                currency=p["currency"],
                asset_category=p["asset_category"],
                last_price=last_price,
                market_value=round(market_value, 2) if market_value is not None else None,
                unrealized_pnl=round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            )
        )

    return schemas.Portfolio(
        positions=enriched,
        usd_sgd_rate=usd_sgd,
        total_market_value_usd=round(total_market_value_usd, 2),
        total_unrealized_pnl_usd=round(total_unrealized_pnl_usd, 2),
        total_market_value_sgd=(
            round(total_market_value_usd * usd_sgd, 2) if usd_sgd is not None else None
        ),
        total_unrealized_pnl_sgd=(
            round(total_unrealized_pnl_usd * usd_sgd, 2) if usd_sgd is not None else None
        ),
    )
