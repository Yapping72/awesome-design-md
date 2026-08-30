from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, func

from .database import Base


class UploadBatch(Base):
    """One CSV upload. Executions record which batch inserted them so an
    import can be reviewed or undone without wiping the whole journal.

    Only newly-inserted fills are attributed to a batch — a fill that was
    already present (skipped as a duplicate on re-upload) keeps belonging to
    whichever batch first inserted it, so deleting a later, overlapping
    upload doesn't remove fills that also came from an earlier one.
    """

    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime, server_default=func.now())


class Execution(Base):
    """A single fill/execution line parsed from an IBKR Activity Statement.

    Realized P/L on opening fills is 0 (IBKR only populates it on closing
    fills); commission is stored separately and netted in at query time so
    daily/weekly/monthly aggregates reflect true net P/L.
    """

    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=False)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=True, index=True)
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


class TradeNote(Base):
    """Journal notes/tags attached to a round-trip trade.

    Round trips aren't stored rows — they're computed on the fly by
    services/round_trips.py from the executions table (FIFO-matching can
    shift if fills are re-imported). We key notes on a synthetic,
    deterministic `round_trip_id` (entry execution id + exit execution id +
    quantity closed) rather than a surrogate id, so a note stays attached
    to "the same round trip" across recomputation as long as the underlying
    fills haven't changed.
    """

    __tablename__ = "trade_notes"

    id = Column(Integer, primary_key=True, index=True)
    round_trip_id = Column(String, unique=True, index=True, nullable=False)
    notes = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # comma-separated; simple by design
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
