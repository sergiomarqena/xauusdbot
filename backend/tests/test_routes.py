from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_route():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_provider_is_explicitly_labelled(monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()
    response = client.get("/api/v1/market/status")
    assert response.status_code == 200
    assert response.json()["data_mode"] in {"demo", "provider"}


def test_candle_route_returns_ohlc():
    response = client.get("/api/v1/market/candles?limit=60")
    assert response.status_code == 200
    body = response.json()
    assert len(body["candles"]) == 60
    assert body["data_mode"] in {"demo", "provider"}
    assert body["candles"][-1]["high"] >= body["candles"][-1]["low"]
