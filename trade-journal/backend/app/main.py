import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from .config import settings
from .database import Base, engine
from .routers import market, pnl, trades, upload

logger = logging.getLogger("trade_journal")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Postgres may still be starting even after its healthcheck passes; retry
    # briefly instead of crash-looping the container.
    last_error: Exception | None = None
    for attempt in range(10):
        try:
            Base.metadata.create_all(bind=engine)
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
