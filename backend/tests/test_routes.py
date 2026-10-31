from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_route():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_gold_key_is_reported_honestly(monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "twelvedata")
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    get_settings.cache_clear()
    response = client.get("/api/v1/market/status")
    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "unavailable"
    assert body["configured"] is False
    get_settings.cache_clear()


def test_demo_provider_is_explicitly_labelled(monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "demo")
    get_settings.cache_clear()
    response = client.get("/api/v1/market/status")
    assert response.status_code == 200
    assert response.json()["data_mode"] == "demo"
    get_settings.cache_clear()


def test_candle_route_returns_explicit_demo_ohlc(monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "demo")
    get_settings.cache_clear()
    response = client.get("/api/v1/market/candles?limit=60")
    assert response.status_code == 200
    body = response.json()
    assert len(body["candles"]) == 60
    assert body["data_mode"] == "demo"
    assert body["candles"][-1]["high"] >= body["candles"][-1]["low"]
    get_settings.cache_clear()


def test_candle_route_does_not_fabricate_live_price_without_key(monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "twelvedata")
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    get_settings.cache_clear()
    response = client.get("/api/v1/market/candles?limit=60")
    assert response.status_code == 503
    assert "TWELVE_DATA_API_KEY" in response.json()["detail"]
    get_settings.cache_clear()
