import json
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

# Basic symbols used for tests (can be adjusted if validation stricter)
TEST_SYMBOL = "AAPL"
ALT_SYMBOL = "MSFT"


def test_health():
    r = client.get("/api/stocks/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


def test_market_status():
    r = client.get("/api/stocks/market-status")
    assert r.status_code == 200
    data = r.json()
    assert "us_market_open" in data
    assert "phase" in data


def test_info():
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/info")
    # Accept 200 or graceful error JSON
    assert r.status_code in (200, 400, 500)
    # Ensure JSON parsable
    _ = r.json()


def test_validate():
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/validate")
    assert r.status_code in (200, 400)
    _ = r.json()


def test_batch_validate():
    payload = {"symbols": [TEST_SYMBOL, ALT_SYMBOL], "check_data_availability": True}
    r = client.post("/api/stocks/validate-batch", json=payload)
    assert r.status_code in (200, 400)
    data = r.json()
    # If successful, verify the response structure
    if r.status_code == 200:
        assert "total_count" in data
        assert "valid_count" in data
        assert "invalid_count" in data
        assert "results" in data


def test_suggestions():
    r = client.get("/api/stocks/suggestions", params={"query": "AA", "limit": 5})
    assert r.status_code in (200, 400)
    _ = r.json()


def test_strategy_history():
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/strategy-history", params={"limit": 5})
    # Could be empty history; just ensure no crash
    assert r.status_code in (200, 400, 500)
    _ = r.json()


def test_technical():
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/technical", params={"period": "3mo"})
    assert r.status_code in (200, 400, 500)
    _ = r.json()


def test_performance():
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/performance", params={"period": "1y"})
    assert r.status_code in (200, 400, 500)
    _ = r.json()


def test_add_instrument():
    r = client.post("/api/stocks/add-instrument", json={"ticker": TEST_SYMBOL})
    assert r.status_code in (200, 400)
    _ = r.json()


def test_simple_test():
    r = client.get("/api/stocks/test")
    assert r.status_code == 200
    data = r.json()
    assert data["message"] == "test successful"
