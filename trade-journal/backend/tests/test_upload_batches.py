import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./_test_startup.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

SAMPLE_CSV = (Path(__file__).parent / "sample_data" / "sample_ibkr_activity.csv").read_bytes()

# A second, non-overlapping statement so a batch delete has a symbol whose
# fills should survive untouched.
OTHER_CSV = b"""Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
Trades,Data,Order,Stocks,USD,NVDA,"2024-02-01, 09:35:00",20,120.00,121.00,-2400,-1,2401,0,20,O
Trades,Data,Order,Stocks,USD,NVDA,"2024-02-02, 10:00:00",-20,130.00,131.00,2600,-1,2401,199,10,C
"""


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
    yield TestClient(app)
    app.dependency_overrides.clear()


def upload(client, content: bytes, filename: str = "statement.csv"):
    return client.post("/api/upload", files={"file": (filename, content, "text/csv")})


def test_upload_creates_a_batch(client):
    res = upload(client, SAMPLE_CSV, "jan_statement.csv")
    assert res.status_code == 200
    assert res.json()["inserted"] == 6

    batches = client.get("/api/uploads").json()
    assert len(batches) == 1
    assert batches[0]["filename"] == "jan_statement.csv"
    assert batches[0]["row_count"] == 6


def test_reupload_creates_a_batch_with_zero_new_rows(client):
    upload(client, SAMPLE_CSV, "first.csv")
    res = upload(client, SAMPLE_CSV, "second.csv")
    assert res.json() == {"parsed": 6, "inserted": 0, "skipped_duplicates": 6}

    batches = client.get("/api/uploads").json()
    assert len(batches) == 2
    by_filename = {b["filename"]: b["row_count"] for b in batches}
    assert by_filename == {"first.csv": 6, "second.csv": 0}


def test_duplicate_fills_keep_original_batch_on_delete(client):
    upload(client, SAMPLE_CSV, "first.csv")
    upload(client, SAMPLE_CSV, "second.csv")  # all duplicates, batch has 0 rows

    batches = client.get("/api/uploads").json()
    second_batch_id = next(b["id"] for b in batches if b["filename"] == "second.csv")

    del_res = client.delete(f"/api/uploads/{second_batch_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted_fills"] == 0

    # The original fills (owned by the first batch) are untouched.
    assert client.get("/api/trades?page_size=100").json()["total"] == 6


def test_delete_batch_removes_only_its_own_fills(client):
    upload(client, SAMPLE_CSV, "aapl_msft_tsla.csv")
    upload(client, OTHER_CSV, "nvda.csv")

    total_before = client.get("/api/trades?page_size=100").json()["total"]
    assert total_before == 8

    batches = client.get("/api/uploads").json()
    nvda_batch_id = next(b["id"] for b in batches if b["filename"] == "nvda.csv")

    del_res = client.delete(f"/api/uploads/{nvda_batch_id}")
    assert del_res.json()["deleted_fills"] == 2

    remaining = client.get("/api/trades?page_size=100").json()
    assert remaining["total"] == 6
    assert all(item["symbol"] != "NVDA" for item in remaining["items"])

    remaining_batches = client.get("/api/uploads").json()
    assert [b["filename"] for b in remaining_batches] == ["aapl_msft_tsla.csv"]


def test_delete_nonexistent_batch_404s(client):
    res = client.delete("/api/uploads/999")
    assert res.status_code == 404


def test_clear_all_trades_also_clears_batches(client):
    upload(client, SAMPLE_CSV)
    assert len(client.get("/api/uploads").json()) == 1

    client.delete("/api/trades")

    assert client.get("/api/uploads").json() == []
    assert client.get("/api/trades").json()["total"] == 0
