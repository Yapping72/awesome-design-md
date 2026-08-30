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
            # Day 1: net +448 (round trip realized 449, commission -1 on close;
            # the opening leg's -1 commission also lands on day 1 since both
            # legs happen the same day here).
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
            # Day 2: net -252
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
        ]
    )
    session.commit()
    session.close()

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_equity_curve_is_cumulative(client):
    res = client.get("/api/pnl/equity-curve")
    assert res.status_code == 200
    points = res.json()
    assert len(points) == 2

    assert points[0]["date"] == "2024-01-02"
    assert points[0]["pnl"] == 447.0  # AAPL day: 449 - 1 (close comm) - 1 (open comm)
    assert points[0]["cumulative_pnl"] == 447.0

    assert points[1]["date"] == "2024-01-03"
    assert points[1]["pnl"] == -253.0  # TSLA day: -251 - 1 - 1
    assert points[1]["cumulative_pnl"] == 447.0 - 253.0


def test_equity_curve_respects_date_range(client):
    res = client.get("/api/pnl/equity-curve?start=2024-01-03")
    points = res.json()
    assert len(points) == 1
    assert points[0]["date"] == "2024-01-03"
    # Cumulative resets within the filtered window rather than carrying
    # over P&L from before `start`.
    assert points[0]["cumulative_pnl"] == -253.0
