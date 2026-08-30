from datetime import datetime, timedelta

from app.services.positions import compute_open_positions


class FakeExecution:
    def __init__(self, symbol, quantity, price, dt, currency="USD", asset_category="Stocks"):
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.trade_datetime = dt
        self.currency = currency
        self.asset_category = asset_category


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *_args, **_kwargs):
        return FakeQuery(self._rows)


def t(offset_minutes: int) -> datetime:
    return datetime(2024, 1, 1) + timedelta(minutes=offset_minutes)


def test_closed_position_is_excluded():
    rows = [
        FakeExecution("AAPL", 100, 185.5, t(0)),
        FakeExecution("AAPL", -100, 190.0, t(1)),
    ]
    positions = compute_open_positions(FakeSession(rows))
    assert positions == []


def test_open_long_position_weighted_average_cost():
    rows = [
        FakeExecution("MSFT", 10, 100.0, t(0)),
        FakeExecution("MSFT", 10, 120.0, t(1)),
    ]
    positions = compute_open_positions(FakeSession(rows))
    assert len(positions) == 1
    assert positions[0]["symbol"] == "MSFT"
    assert positions[0]["quantity"] == 20
    assert positions[0]["avg_cost"] == 110.0  # (10*100 + 10*120) / 20


def test_partial_reduction_keeps_average_cost():
    rows = [
        FakeExecution("TSLA", 10, 200.0, t(0)),
        FakeExecution("TSLA", -4, 250.0, t(1)),
    ]
    positions = compute_open_positions(FakeSession(rows))
    assert positions[0]["quantity"] == 6
    assert positions[0]["avg_cost"] == 200.0


def test_flip_through_zero_resets_cost_basis():
    rows = [
        FakeExecution("NFLX", 10, 100.0, t(0)),
        FakeExecution("NFLX", -15, 150.0, t(1)),  # sells all 10 then shorts 5 more
    ]
    positions = compute_open_positions(FakeSession(rows))
    assert positions[0]["quantity"] == -5
    assert positions[0]["avg_cost"] == 150.0


def test_short_position_supported():
    rows = [FakeExecution("GME", -20, 30.0, t(0))]
    positions = compute_open_positions(FakeSession(rows))
    assert positions[0]["quantity"] == -20
    assert positions[0]["avg_cost"] == 30.0


def test_multiple_symbols_only_open_ones_returned():
    rows = [
        FakeExecution("AAPL", 100, 185.5, t(0)),
        FakeExecution("AAPL", -100, 190.0, t(1)),
        FakeExecution("MSFT", 10, 370.0, t(2)),
    ]
    positions = compute_open_positions(FakeSession(rows))
    assert [p["symbol"] for p in positions] == ["MSFT"]
