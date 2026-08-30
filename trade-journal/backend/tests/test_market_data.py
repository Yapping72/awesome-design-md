from app.services import market_data


def test_get_quote_returns_none_on_fetch_failure(monkeypatch):
    market_data._cache.clear()

    def boom(_symbol):
        raise RuntimeError("network blocked")

    monkeypatch.setattr(market_data, "_fetch_last_price", boom)
    assert market_data.get_quote("AAPL") is None


def test_get_fx_rate_returns_none_on_fetch_failure(monkeypatch):
    market_data._cache.clear()

    def boom(_symbol):
        raise RuntimeError("network blocked")

    monkeypatch.setattr(market_data, "_fetch_last_price", boom)
    assert market_data.get_fx_rate("USDSGD") is None


def test_quote_is_cached_within_ttl(monkeypatch):
    market_data._cache.clear()
    calls = []

    def fake_fetch(symbol):
        calls.append(symbol)
        return 123.45

    monkeypatch.setattr(market_data, "_fetch_last_price", fake_fetch)
    assert market_data.get_quote("AAPL") == 123.45
    assert market_data.get_quote("AAPL") == 123.45
    assert calls == ["AAPL"]  # second call served from cache, no re-fetch


def test_get_quotes_fetches_each_symbol(monkeypatch):
    market_data._cache.clear()
    monkeypatch.setattr(market_data, "_fetch_last_price", lambda s: {"AAPL": 200.0, "TSLA": 250.0}[s])
    result = market_data.get_quotes(["AAPL", "TSLA"])
    assert result == {"AAPL": 200.0, "TSLA": 250.0}
