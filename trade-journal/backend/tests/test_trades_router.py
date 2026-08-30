import os
from datetime import datetime

# Set before importing app.* — app.database builds its engine from this at
# import time, and app.main's startup event calls create_all against it. A
# harmless local sqlite file keeps that startup event from trying (and
# retrying, for ~20s, then failing) to reach a real Postgres instance that
# won't exist in a test environment.
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
                external_id="e1",
                symbol="AAPL",
                trade_datetime=datetime(2024, 1, 2, 9, 31),
                trade_date=datetime(2024, 1, 2).date(),
                quantity=100,
                price=185.5,
                proceeds=-18550,
                commission=-1.0,
                realized_pnl=0.0,
                code="O",
            ),
            Execution(
                external_id="e2",
                symbol="AAPL",
                trade_datetime=datetime(2024, 1, 2, 15, 45),
                trade_date=datetime(2024, 1, 2).date(),
                quantity=-100,
                price=190.0,
                proceeds=19000,
                commission=-1.0,
                realized_pnl=449.0,
                code="C",
            ),
        ]
    )
    session.commit()
    session.close()

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_round_trips_endpoint_returns_matched_trade(client):
    res = client.get("/api/trades/round-trips")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    rt = body["items"][0]
    assert rt["symbol"] == "AAPL"
    assert rt["realized_pnl"] == 448.0
    assert rt["notes"] is None
    assert rt["tags"] == []


def test_notes_upsert_round_trips_through_get(client):
    round_trip_id = client.get("/api/trades/round-trips").json()["items"][0]["round_trip_id"]

    put_res = client.put(
        f"/api/trades/round-trips/{round_trip_id}/notes",
        json={"notes": "Broke out of a tight range, held through lunch chop.", "tags": ["breakout", "swing"]},
    )
    assert put_res.status_code == 200
    assert put_res.json()["tags"] == ["breakout", "swing"]

    get_res = client.get("/api/trades/round-trips")
    rt = get_res.json()["items"][0]
    assert rt["notes"] == "Broke out of a tight range, held through lunch chop."
    assert rt["tags"] == ["breakout", "swing"]


def test_notes_upsert_overwrites_previous_value(client):
    round_trip_id = client.get("/api/trades/round-trips").json()["items"][0]["round_trip_id"]

    client.put(f"/api/trades/round-trips/{round_trip_id}/notes", json={"notes": "first draft", "tags": ["a"]})
    client.put(f"/api/trades/round-trips/{round_trip_id}/notes", json={"notes": "revised", "tags": ["b", "c"]})

    rt = client.get("/api/trades/round-trips").json()["items"][0]
    assert rt["notes"] == "revised"
    assert rt["tags"] == ["b", "c"]


def test_empty_notes_and_tags_clear_stored_value(client):
    round_trip_id = client.get("/api/trades/round-trips").json()["items"][0]["round_trip_id"]

    client.put(f"/api/trades/round-trips/{round_trip_id}/notes", json={"notes": "temporary", "tags": ["x"]})
    client.put(f"/api/trades/round-trips/{round_trip_id}/notes", json={"notes": "", "tags": []})

    rt = client.get("/api/trades/round-trips").json()["items"][0]
    assert rt["notes"] is None
    assert rt["tags"] == []
