from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    asset_category: Optional[str] = None
    currency: Optional[str] = None
    trade_datetime: datetime
    trade_date: date
    quantity: float
    price: float
    proceeds: Optional[float] = None
    commission: Optional[float] = None
    realized_pnl: float
    net_pnl: float
    code: Optional[str] = None


class TradesPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TradeOut]


class RoundTripOut(BaseModel):
    round_trip_id: str
    symbol: str
    side: str
    quantity: float
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    commission: float
    realized_pnl: float
    hold_seconds: float
    notes: Optional[str] = None
    tags: list[str] = []


class TradeNoteIn(BaseModel):
    notes: Optional[str] = None
    tags: list[str] = []


class TradeNoteOut(BaseModel):
    round_trip_id: str
    notes: Optional[str] = None
    tags: list[str] = []


class RoundTripsPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RoundTripOut]


class UploadResult(BaseModel):
    parsed: int
    inserted: int
    skipped_duplicates: int


class PeriodPnl(BaseModel):
    period: date
    pnl: float
    trade_count: int


class DayPnl(BaseModel):
    date: date
    pnl: float
    trade_count: int


class EquityPoint(BaseModel):
    date: date
    pnl: float
    cumulative_pnl: float


class FxRate(BaseModel):
    pair: str
    rate: Optional[float] = None


class Position(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    currency: Optional[str] = None
    asset_category: Optional[str] = None
    last_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None


class Portfolio(BaseModel):
    positions: list[Position]
    usd_sgd_rate: Optional[float] = None
    total_market_value_usd: float
    total_unrealized_pnl_usd: float
    total_market_value_sgd: Optional[float] = None
    total_unrealized_pnl_sgd: Optional[float] = None


class Summary(BaseModel):
    total_pnl: float
    total_trades: int
    closing_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: Optional[float] = None
    best_day: Optional[DayPnl] = None
    worst_day: Optional[DayPnl] = None
