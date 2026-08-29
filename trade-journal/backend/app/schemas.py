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
