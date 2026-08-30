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
            Execution(
                external_id="e1", symbol="AAPL",
                trade_datetime=datetime(2024, 1, 2, 9, 31), trade_date=datetime(2024, 1, 2).date(),
                quantity=100, price=185.5, commission=-1.0, realized_pnl=0.0, code="O",
            ),
            Execution(
                external_id="e2", symbol="AAPL",
                trade_datetime=datetime(2024, 1, 2, 15, 45), trade_date=datetime(2024, 1, 2).date(),
                quantity=-100, price=190.0, commission=-1.0, realized_pnl=449.0, code="C",
            ),
        ]
    )
    session.commit()
    session.close()

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_export_trades_csv(client):
    res = client.get("/api/trades/export")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "attachment" in res.headers["content-disposition"]
    lines = res.text.strip().splitlines()
    assert lines[0] == "trade_datetime,symbol,asset_category,currency,quantity,price,proceeds,commission,realized_pnl,net_pnl,code"
    assert len(lines) == 3  # header + 2 fills


def test_export_round_trips_csv(client):
    res = client.get("/api/trades/round-trips/export")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    lines = res.text.strip().splitlines()
    assert lines[0] == "symbol,side,quantity,entry_time,exit_time,entry_price,exit_price,commission,realized_pnl,hold_seconds,tags,notes"
    assert len(lines) == 2  # header + 1 round trip
    assert "AAPL,long,100" in lines[1]


def test_export_daily_pnl_csv(client):
    res = client.get("/api/pnl/export")
    assert res.status_code == 200
    lines = res.text.strip().splitlines()
    assert lines[0] == "date,pnl,trade_count"
    assert lines[1] == "2024-01-02,447.0,2"


def test_export_trades_respects_symbol_filter(client):
    res = client.get("/api/trades/export?symbol=MSFT")
    lines = res.text.strip().splitlines()
    assert len(lines) == 1  # header only, no matching rows
