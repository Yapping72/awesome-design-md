import os
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "sqlite:///./_test_startup.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Execution


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = TestingSession()
    session.add_all(
        [
            # AAPL: closes 2024-01-02, net +448
            Execution(
                external_id="e1", symbol="AAPL",
                trade_datetime=datetime(2024, 1, 2, 9, 31), trade_date=datetime(2024, 1, 2).date(),
                quantity=100, price=185.5, commission=-1.0, realized_pnl=0.0,
            ),
            Execution(
                external_id="e2", symbol="AAPL",
                trade_datetime=datetime(2024, 1, 2, 15, 45), trade_date=datetime(2024, 1, 2).date(),
                quantity=-100, price=190.0, commission=-1.0, realized_pnl=449.0,
            ),
            # TSLA: closes 2024-01-03, net -252
            Execution(
                external_id="e3", symbol="TSLA",
                trade_datetime=datetime(2024, 1, 3, 10, 5), trade_date=datetime(2024, 1, 3).date(),
                quantity=50, price=240.0, commission=-1.0, realized_pnl=0.0,
            ),
            Execution(
                external_id="e4", symbol="TSLA",
                trade_datetime=datetime(2024, 1, 3, 14, 22), trade_date=datetime(2024, 1, 3).date(),
                quantity=-50, price=235.0, commission=-1.0, realized_pnl=-251.0,
            ),
            # MSFT: closes 2024-01-05, net +148
            Execution(
                external_id="e5", symbol="MSFT",
                trade_datetime=datetime(2024, 1, 5, 9, 40), trade_date=datetime(2024, 1, 5).date(),
                quantity=30, price=370.0, commission=-1.0, realized_pnl=0.0,
            ),
            Execution(
                external_id="e6", symbol="MSFT",
                trade_datetime=datetime(2024, 1, 5, 11, 12), trade_date=datetime(2024, 1, 5).date(),
                quantity=-30, price=375.0, commission=-1.0, realized_pnl=149.0,
            ),
        ]
    )
    session.commit()
    session.close()

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_fills_sort_by_net_pnl_ascending(client):
    res = client.get("/api/trades?sort_by=net_pnl&sort_dir=asc&page_size=100")
    pnls = [item["net_pnl"] for item in res.json()["items"]]
    assert pnls == sorted(pnls)
    assert pnls[0] == -252.0  # TSLA's closing fill is the worst


def test_fills_sort_by_symbol_ascending(client):
    res = client.get("/api/trades?sort_by=symbol&sort_dir=asc&page_size=100")
    symbols = [item["symbol"] for item in res.json()["items"]]
    assert symbols == sorted(symbols)


def test_fills_default_sort_is_trade_datetime_desc(client):
    res = client.get("/api/trades?page_size=100")
    datetimes = [item["trade_datetime"] for item in res.json()["items"]]
    assert datetimes == sorted(datetimes, reverse=True)


def test_fills_date_range_filter(client):
    res = client.get("/api/trades?start=2024-01-03&end=2024-01-03")
    items = res.json()["items"]
    assert len(items) == 2
    assert all(item["symbol"] == "TSLA" for item in items)


def test_round_trips_sort_by_realized_pnl(client):
    res = client.get("/api/trades/round-trips?sort_by=realized_pnl&sort_dir=asc")
    pnls = [item["realized_pnl"] for item in res.json()["items"]]
    assert pnls == [-252.0, 148.0, 448.0]


def test_round_trips_date_range_filter(client):
    res = client.get("/api/trades/round-trips?start=2024-01-05&end=2024-01-05")
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["symbol"] == "MSFT"


def test_round_trips_default_sort_is_exit_time_desc(client):
    res = client.get("/api/trades/round-trips")
    symbols = [item["symbol"] for item in res.json()["items"]]
    assert symbols == ["MSFT", "TSLA", "AAPL"]  # most recent exit first
