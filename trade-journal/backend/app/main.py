import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from .config import settings
from .routers import market, pnl, trades, upload

logger = logging.getLogger("trade_journal")

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Postgres may still be starting even after its healthcheck passes; retry
    # briefly instead of crash-looping the container. Schema is managed by
    # Alembic migrations (alembic/versions/), not create_all — this runs the
    # same `alembic upgrade head` a deploy would run manually, so a fresh
    # container is ready to serve without an extra manual step.
    last_error: Exception | None = None
    for attempt in range(10):
        try:
            command.upgrade(_alembic_config(), "head")
            break
        except OperationalError as exc:
            last_error = exc
            logger.warning("Database not ready (attempt %s/10): %s", attempt + 1, exc)
            time.sleep(2)
    else:
        raise RuntimeError("Could not connect to the database") from last_error
    yield


app = FastAPI(title="Trade Journal API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(trades.router)
app.include_router(pnl.router)
app.include_router(market.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
