from fastapi.testclient import TestClient

from trading_user_stats.app.api import create_app
from trading_user_stats.app.config import Settings


def test_dashboard_and_analytics_endpoints(tmp_path):
    settings = Settings(
        database_path=tmp_path / "stats.sqlite3",
        demo_trade_count=30,
        seed_demo_on_startup=True,
    )
    with TestClient(create_app(settings)) as client:
        accounts = client.get("/api/accounts")
        assert accounts.status_code == 200
        assert len(accounts.json()) == 10

        overview = client.get("/api/overview?user=demo_01&range=all")
        assert overview.status_code == 200
        assert overview.json()["closed_trades"] == 3
        assert overview.json()["account"]["is_demo"] is True

        stats = client.get("/api/stats?user_id=demo_01&range=all")
        assert stats.status_code == 200
        assert stats.json()["summary"]["trade_count"] == 3

        assert client.get("/api/date-ranges?user_id=demo_01").status_code == 200
        assert client.get("/api/daily-pnl?user=demo_01&range=all").status_code == 200
        assert client.get("/api/breakdown?user=demo_01&range=all&by=symbol").status_code == 200
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/").status_code == 200
        assert client.get("/static/app.js").status_code == 200


def test_unknown_accounts_and_invalid_ranges_return_client_errors(tmp_path):
    settings = Settings(database_path=tmp_path / "stats.sqlite3", demo_trade_count=0)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/overview?user=missing").status_code == 404
        invalid = client.get(
            "/api/overview?user=demo_01&range=custom&start=2026-02-02&end=2026-01-01"
        )
        assert invalid.status_code == 422


def test_demo_seed_does_not_expose_real_accounts(tmp_path):
    settings = Settings(database_path=tmp_path / "stats.sqlite3", demo_trade_count=0)
    with TestClient(create_app(settings)) as client:
        connection = client.app.state.settings.database_path
        import sqlite3

        with sqlite3.connect(connection) as db:
            db.execute(
                """INSERT INTO accounts
                   (user_id, name, currency, start_balance, tz, is_demo)
                   VALUES ('real', 'Real account', 'USD', 1000, 'UTC', 0)"""
            )
        response = client.get("/api/overview?user=real&range=all")
        assert response.status_code == 403
