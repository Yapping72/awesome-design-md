"""Live market data via yfinance (Yahoo Finance).

There's no supported public API for Google Finance, so yfinance is the
practical choice for a Python backend. Quotes and FX rates are cached
in-process for a short TTL so a dashboard polling every few seconds doesn't
hammer Yahoo or get rate-limited.
"""

import logging
import threading
import time
from typing import Optional

import yfinance as yf

logger = logging.getLogger("trade_journal.market_data")

_CACHE_TTL_SECONDS = 30
_cache: dict[str, tuple[Optional[float], float]] = {}
_lock = threading.Lock()


def _cached(key: str, fetch_fn) -> Optional[float]:
    now = time.time()
    with _lock:
        entry = _cache.get(key)
        if entry is not None and now - entry[1] < _CACHE_TTL_SECONDS:
            return entry[0]

    try:
        value = fetch_fn()
    except Exception:
        logger.warning("Market data fetch failed for %s", key, exc_info=True)
        value = None

    with _lock:
        _cache[key] = (value, now)
    return value


def _fetch_last_price(symbol: str) -> Optional[float]:
    price = yf.Ticker(symbol).fast_info.last_price
    return float(price) if price is not None else None


def get_quote(symbol: str) -> Optional[float]:
    return _cached(f"quote:{symbol}", lambda: _fetch_last_price(symbol))


def get_quotes(symbols: list[str]) -> dict[str, Optional[float]]:
    return {symbol: get_quote(symbol) for symbol in symbols}


def get_fx_rate(pair: str = "USDSGD") -> Optional[float]:
    return _cached(f"fx:{pair}", lambda: _fetch_last_price(f"{pair}=X"))
