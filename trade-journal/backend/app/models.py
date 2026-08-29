from sqlalchemy import Column, Date, DateTime, Float, Integer, String, func

from .database import Base


class Execution(Base):
    """A single fill/execution line parsed from an IBKR Activity Statement.

    Realized P/L on opening fills is 0 (IBKR only populates it on closing
    fills); commission is stored separately and netted in at query time so
    daily/weekly/monthly aggregates reflect true net P/L.
    """

    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=False)
    account_id = Column(String, nullable=True)
    asset_category = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    symbol = Column(String, index=True, nullable=False)
    trade_datetime = Column(DateTime, index=True, nullable=False)
    trade_date = Column(Date, index=True, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    proceeds = Column(Float, nullable=True)
    commission = Column(Float, nullable=True, default=0.0)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    code = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
