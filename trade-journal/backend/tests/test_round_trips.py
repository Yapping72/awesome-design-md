from datetime import datetime, timedelta

from app.services.round_trips import aggregate_by_symbol, compute_round_trips


class FakeExecution:
    def __init__(self, id_, symbol, quantity, price, dt, commission=-1.0):
        self.id = id_
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.trade_datetime = dt
        self.commission = commission


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


def test_simple_long_round_trip():
    rows = [
        FakeExecution(1, "AAPL", 100, 185.5, t(0), commission=-1.0),
        FakeExecution(2, "AAPL", -100, 190.0, t(60), commission=-1.0),
    ]
    trips = compute_round_trips(FakeSession(rows))
    assert len(trips) == 1
    rt = trips[0]
    assert rt["side"] == "long"
    assert rt["quantity"] == 100
    assert rt["entry_price"] == 185.5
    assert rt["exit_price"] == 190.0
    assert rt["commission"] == -2.0
    # gross = (190 - 185.5) * 100 = 450; net = 450 - 2 = 448
    assert rt["realized_pnl"] == 448.0
    assert rt["hold_seconds"] == 3600


def test_simple_short_round_trip():
    rows = [
        FakeExecution(1, "TSLA", -50, 240.0, t(0)),
        FakeExecution(2, "TSLA", 50, 235.0, t(30)),
    ]
    trips = compute_round_trips(FakeSession(rows))
    assert len(trips) == 1
    rt = trips[0]
    assert rt["side"] == "short"
    # gross = (240 - 235) * 50 = 250 (profit on a short when price drops)
    assert rt["realized_pnl"] == 248.0  # 250 - 2 commission


def test_fifo_matches_earliest_lot_first():
    rows = [
        FakeExecution(1, "MSFT", 10, 100.0, t(0)),   # lot A
        FakeExecution(2, "MSFT", 10, 110.0, t(10)),  # lot B
        FakeExecution(3, "MSFT", -10, 150.0, t(20)), # closes lot A only (FIFO)
    ]
    trips = compute_round_trips(FakeSession(rows))
    assert len(trips) == 1
    assert trips[0]["entry_price"] == 100.0  # matched against lot A, not B
    assert trips[0]["quantity"] == 10


def test_closing_fill_spans_multiple_lots():
    rows = [
        FakeExecution(1, "NFLX", 5, 100.0, t(0)),   # lot A: 5 @ 100
        FakeExecution(2, "NFLX", 5, 110.0, t(10)),  # lot B: 5 @ 110
        FakeExecution(3, "NFLX", -10, 150.0, t(20)),  # closes both lots
    ]
    trips = compute_round_trips(FakeSession(rows))
    assert len(trips) == 2
    assert trips[0]["entry_price"] == 100.0
    assert trips[0]["quantity"] == 5
    assert trips[1]["entry_price"] == 110.0
    assert trips[1]["quantity"] == 5


def test_partial_close_leaves_position_open():
    rows = [
        FakeExecution(1, "GME", 10, 20.0, t(0)),
        FakeExecution(2, "GME", -4, 25.0, t(10)),
    ]
    trips = compute_round_trips(FakeSession(rows))
    assert len(trips) == 1
    assert trips[0]["quantity"] == 4
    # remaining 6 shares still open -> no second round trip yet


def test_flip_through_zero_produces_close_and_new_open():
    rows = [
        FakeExecution(1, "AMD", 10, 100.0, t(0)),
        FakeExecution(2, "AMD", -15, 90.0, t(10)),  # closes the 10 long, opens 5 short
        FakeExecution(3, "AMD", 5, 80.0, t(20)),  # closes the 5 short
    ]
    trips = compute_round_trips(FakeSession(rows))
    assert len(trips) == 2
    assert trips[0]["side"] == "long"
    assert trips[0]["quantity"] == 10
    assert trips[1]["side"] == "short"
    assert trips[1]["quantity"] == 5
    assert trips[1]["entry_price"] == 90.0
    assert trips[1]["exit_price"] == 80.0


def test_no_close_yields_no_round_trips():
    rows = [FakeExecution(1, "SPY", 10, 450.0, t(0))]
    assert compute_round_trips(FakeSession(rows)) == []


def test_round_trip_id_is_stable_and_unique():
    rows = [
        FakeExecution(1, "NFLX", 5, 100.0, t(0)),
        FakeExecution(2, "NFLX", 5, 110.0, t(10)),
        FakeExecution(3, "NFLX", -10, 150.0, t(20)),  # closes both lots
    ]
    trips = compute_round_trips(FakeSession(rows))
    ids = [rt["round_trip_id"] for rt in trips]
    assert len(ids) == len(set(ids))  # unique per round trip
    assert ids == ["1:3", "2:3"]  # entry execution id : exit execution id

    # Recomputing from the same executions must produce the same ids.
    trips_again = compute_round_trips(FakeSession(rows))
    assert [rt["round_trip_id"] for rt in trips_again] == ids


def test_aggregate_by_symbol_groups_and_ranks_by_total_pnl():
    rows = [
        # AAPL: one win (+448)
        FakeExecution(1, "AAPL", 100, 185.5, t(0)),
        FakeExecution(2, "AAPL", -100, 190.0, t(60)),
        # TSLA: one loss (-252)
        FakeExecution(3, "TSLA", 50, 240.0, t(0)),
        FakeExecution(4, "TSLA", -50, 235.0, t(30)),
        # MSFT: two wins
        FakeExecution(5, "MSFT", 10, 100.0, t(0)),
        FakeExecution(6, "MSFT", -10, 110.0, t(10)),
        FakeExecution(7, "MSFT", 10, 100.0, t(20)),
        FakeExecution(8, "MSFT", -10, 105.0, t(30)),
    ]
    trips = compute_round_trips(FakeSession(rows))
    perf = aggregate_by_symbol(trips)

    by_symbol = {p["symbol"]: p for p in perf}
    assert by_symbol["AAPL"]["trade_count"] == 1
    assert by_symbol["AAPL"]["wins"] == 1
    assert by_symbol["AAPL"]["losses"] == 0
    assert by_symbol["AAPL"]["win_rate"] == 100.0

    assert by_symbol["TSLA"]["wins"] == 0
    assert by_symbol["TSLA"]["losses"] == 1
    assert by_symbol["TSLA"]["win_rate"] == 0.0

    assert by_symbol["MSFT"]["trade_count"] == 2
    assert by_symbol["MSFT"]["wins"] == 2

    # Ranked by total P&L descending: AAPL (448) > MSFT (146) > TSLA (-252)
    assert [p["symbol"] for p in perf] == ["AAPL", "MSFT", "TSLA"]


def test_aggregate_by_symbol_empty_input():
    assert aggregate_by_symbol([]) == []
