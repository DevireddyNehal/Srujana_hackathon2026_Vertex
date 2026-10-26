from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.journal import storage
from backend.main import app


def test_journal_router_is_mounted_and_scoped_to_demo_user(tmp_path, monkeypatch):
    path = tmp_path / "journal.sqlite3"
    monkeypatch.setattr(storage, "database_path", lambda: path)
    with TestClient(app) as client:
        response = client.post("/api/journal/trades", json={
            "symbol": "MSFT",
            "side": "short",
            "quantity": 1,
            "entry_price": 100,
            "exit_price": 90,
            "opened_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
            "closed_at": datetime(2026, 1, 1, 1, tzinfo=timezone.utc).isoformat(),
            "fees": 1,
            "stop_loss": 105,
            "strategy": "reversal",
        })
        assert response.status_code == 201
        trade_id = response.json()["id"]
        assert response.json()["net_pnl"] == 9
        assert client.get("/api/journal/analytics").json()["summary"]["trade_count"] == 1
        assert client.post(f"/api/journal/trades/{trade_id}/review").status_code == 200
        assert client.delete(f"/api/journal/trades/{trade_id}").status_code == 204


def test_journal_rejects_timezone_naive_trade(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "database_path", lambda: tmp_path / "journal.sqlite3")
    with TestClient(app) as client:
        response = client.post("/api/journal/trades", json={
            "symbol": "MSFT",
            "side": "long",
            "quantity": 1,
            "entry_price": 100,
            "opened_at": "2026-01-01T00:00:00",
        })
        assert response.status_code == 422


def test_journal_cross_device_isolation(tmp_path, monkeypatch):
    """Verify different devices/laptops on /api/journal are completely isolated."""
    path = tmp_path / "journal_isolation.sqlite3"
    monkeypatch.setattr(storage, "database_path", lambda: path)
    with TestClient(app) as client:
        headers_a = {"X-Device-Id": "laptop_alice_789"}
        headers_b = {"X-Device-Id": "laptop_bob_456"}

        # Alice creates trade
        res_a = client.post("/api/journal/trades", json={
            "symbol": "AAPL",
            "side": "long",
            "quantity": 5,
            "entry_price": 150,
            "exit_price": 160,
            "opened_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
            "closed_at": datetime(2026, 1, 1, 2, tzinfo=timezone.utc).isoformat(),
            "fees": 2,
            "strategy": "trend",
        }, headers=headers_a)
        assert res_a.status_code == 201

        # Bob lists trades - must see 0 trades
        res_b = client.get("/api/journal/trades", headers=headers_b)
        assert res_b.status_code == 200
        assert len(res_b.json()["trades"]) == 0

        # Alice lists trades - must see 1 trade
        res_a_list = client.get("/api/journal/trades", headers=headers_a)
        assert res_a_list.status_code == 200
        assert len(res_a_list.json()["trades"]) == 1

