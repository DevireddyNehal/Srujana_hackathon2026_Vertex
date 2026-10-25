from trading_user_stats.app import db, stats
from trading_user_stats.app.seed_demo import seed_demo_trades


def test_stats_on_100k_demo_rows(tmp_path):
    path = tmp_path / "large.sqlite3"
    assert seed_demo_trades(path, 100_000) == 100_000

    connection = db.connect(path)
    try:
        total = 0
        for account in stats.list_accounts(connection):
            result = stats.overview(connection, account["user_id"], "all")
            total += result["closed_trades"]
            assert sum(day["trades"] for day in result["daily_pnl"]["days"]) == result["closed_trades"]
            assert round(sum(day["net_pnl"] for day in result["daily_pnl"]["days"]), 2) == result["net_pnl"]
        assert total == 100_000
    finally:
        connection.close()
