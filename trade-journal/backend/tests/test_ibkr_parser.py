from datetime import datetime
from pathlib import Path

from app.parsers.ibkr import parse_ibkr_activity_csv

SAMPLE_PATH = Path(__file__).parent / "sample_data" / "sample_ibkr_activity.csv"


def load_sample() -> str:
    return SAMPLE_PATH.read_text()


def test_parses_only_trade_rows():
    executions = parse_ibkr_activity_csv(load_sample())
    assert len(executions) == 6
    assert {e["symbol"] for e in executions} == {"AAPL", "TSLA", "MSFT"}


def test_extracts_fields_correctly():
    executions = parse_ibkr_activity_csv(load_sample())
    aapl_close = next(
        e for e in executions if e["symbol"] == "AAPL" and e["realized_pnl"] != 0
    )
    assert aapl_close["quantity"] == -100
    assert aapl_close["price"] == 190
    assert aapl_close["realized_pnl"] == 449
    assert aapl_close["commission"] == -1
    assert aapl_close["trade_datetime"] == datetime(2024, 1, 2, 15, 45, 0)
    assert aapl_close["trade_date"] == datetime(2024, 1, 2, 15, 45, 0).date()
    assert aapl_close["asset_category"] == "Stocks"
    assert aapl_close["currency"] == "USD"


def test_opening_fills_have_zero_realized_pnl():
    executions = parse_ibkr_activity_csv(load_sample())
    aapl_open = next(
        e for e in executions if e["symbol"] == "AAPL" and e["quantity"] > 0
    )
    assert aapl_open["realized_pnl"] == 0


def test_external_id_is_stable_and_unique():
    executions = parse_ibkr_activity_csv(load_sample())
    ids = [e["external_id"] for e in executions]
    assert len(ids) == len(set(ids))

    # Re-parsing the same content must yield identical ids (idempotent import).
    executions2 = parse_ibkr_activity_csv(load_sample())
    assert ids == [e["external_id"] for e in executions2]


def test_ignores_non_trade_sections():
    executions = parse_ibkr_activity_csv(load_sample())
    assert all(e["symbol"] != "" for e in executions)


def test_empty_content_returns_empty_list():
    assert parse_ibkr_activity_csv("") == []


def test_no_trades_section_returns_empty_list():
    content = "Statement,Header,Field Name,Field Value\nStatement,Data,BrokerName,IBKR\n"
    assert parse_ibkr_activity_csv(content) == []
