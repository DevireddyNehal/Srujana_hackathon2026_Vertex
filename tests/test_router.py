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
