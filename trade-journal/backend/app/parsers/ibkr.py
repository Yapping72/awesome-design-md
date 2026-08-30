"""Parser for Interactive Brokers "Activity Statement" CSV exports.

IBKR activity statement CSVs are multi-section: every row starts with a
section name (e.g. "Trades", "Statement", "Positions") followed by either
"Header" (defines the column names for that section) or "Data" (an actual
row). Only the "Trades" section is relevant for a trade journal.

Typical trades header/row pair::

    Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
    Trades,Data,Order,Stocks,USD,AAPL,"2024-01-02, 09:31:00",100,185.5,186.2,-18550,-1,18551,0,70,O
    Trades,Data,Order,Stocks,USD,AAPL,"2024-01-05, 10:15:00",-100,190,190,19000,-1,18551,449,0,C

IBKR only populates "Realized P/L" on the fill(s) that close a position;
opening fills carry 0. Summing "Realized P/L" (net of commission) per date
therefore gives the correct realized daily P/L without needing our own
FIFO/lot-matching engine.
"""

import csv
import hashlib
from datetime import datetime
from io import StringIO
from typing import Any

TRADE_SECTION = "Trades"
# DataDiscriminator values that represent an actual executed fill (as
# opposed to summary/total rows IBKR sometimes injects, e.g. "SubTotal").
VALID_DISCRIMINATORS = {"Order", "Trade", "Execution", ""}

_DATETIME_FORMATS = (
    "%Y-%m-%d, %H:%M:%S",
    "%Y-%m-%d,%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y%m%d;%H%M%S",
    "%Y-%m-%d",
)


class IBKRParseError(ValueError):
    pass


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _parse_datetime(raw: str) -> datetime:
    text = raw.strip().strip('"')
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise IBKRParseError(f"Unrecognized IBKR date/time format: {raw!r}")


def _make_external_id(*parts: Any) -> str:
    key = "|".join(str(p) for p in parts)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def parse_ibkr_activity_csv(content: str) -> list[dict[str, Any]]:
    """Parse an IBKR Activity Statement CSV and return a list of execution dicts.

    Only rows belonging to the "Trades" section are extracted. Raises
    IBKRParseError if the content cannot be parsed as CSV at all; returns an
    empty list (not an error) if no Trades section is found, so callers can
    decide how to surface "nothing to import".
    """
    reader = csv.reader(StringIO(content))
    header: list[str] | None = None
    executions: list[dict[str, Any]] = []

    for row in reader:
        if len(row) < 2:
            continue
        section, row_type = row[0], row[1]
        if section != TRADE_SECTION:
            continue

        if row_type == "Header":
            header = row
            continue

        if row_type != "Data" or header is None:
            continue

        record = dict(zip(header, row))
        discriminator = record.get("DataDiscriminator", "")
        if discriminator not in VALID_DISCRIMINATORS:
            continue

        symbol = (record.get("Symbol") or "").strip()
        dt_raw = record.get("Date/Time") or record.get("Date")
        if not symbol or not dt_raw:
            continue

        trade_dt = _parse_datetime(dt_raw)
        quantity = _to_float(record.get("Quantity"))
        price = _to_float(record.get("T. Price"))
        proceeds = _to_float(record.get("Proceeds"))
        commission = _to_float(record.get("Comm/Fee") or record.get("Comm in USD"))
        realized_pnl = _to_float(
            record.get("Realized P/L") or record.get("Realized P/L in USD")
        )
        account_id = record.get("Account") or record.get("ClientAccountID") or None

        external_id = _make_external_id(
            account_id, symbol, dt_raw, quantity, price, proceeds
        )

        executions.append(
            {
                "external_id": external_id,
                "account_id": account_id,
                "asset_category": record.get("Asset Category") or None,
                "currency": record.get("Currency") or None,
                "symbol": symbol,
                "trade_datetime": trade_dt,
                "trade_date": trade_dt.date(),
                "quantity": quantity,
                "price": price,
                "proceeds": proceeds,
                "commission": commission,
                "realized_pnl": realized_pnl,
                "code": record.get("Code") or None,
            }
        )

    return executions
