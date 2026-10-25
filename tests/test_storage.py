from datetime import datetime, timezone

from backend.journal.schemas import TradeCreate
from backend.journal.storage import (
    create_trade,
    delete_trade,
    get_trade,
    initialize_storage,
    list_trades,
    update_trade,
)


def sample_trade(**changes):
    payload = {
        "symbol": "aapl",
        "side": "long",
        "quantity": 2,
        "entry_price": 100,
        "exit_price": 110,
        "opened_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "closed_at": datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        "fees": 1,
        "stop_loss": 95,
        "strategy": "breakout",
    }
    payload.update(changes)
    return TradeCreate(**payload)


def test_create_list_update_delete_and_user_scope(tmp_path):
    path = tmp_path / "journal.sqlite3"
    initialize_storage(path)
    created = create_trade("demo", sample_trade(), path)
    assert created["symbol"] == "AAPL"
    assert created["net_pnl"] == 19
    assert get_trade("other-user", created["id"], path) is None

    assert update_trade("demo", created["id"], {"notes": "Followed plan"}, path)["notes"] == "Followed plan"
    trades, total = list_trades("demo", limit=10, path=path)
    assert total == len(trades) == 1
    assert delete_trade("demo", created["id"], path)
    assert get_trade("demo", created["id"], path) is None


def test_reject_inconsistent_trade_updates(tmp_path):
    path = tmp_path / "journal.sqlite3"
    initialize_storage(path)
    created = create_trade("demo", sample_trade(), path)
    try:
        update_trade("demo", created["id"], {"closed_at": None}, path)
    except ValueError as error:
        assert "exit_price" in str(error)
    else:
        raise AssertionError("inconsistent close fields were accepted")
