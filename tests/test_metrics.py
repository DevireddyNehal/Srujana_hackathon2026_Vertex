from backend.journal.metrics import trade_metrics


def test_long_and_short_net_pnl_and_r_multiple():
    long_trade = {
        "side": "long", "quantity": 2, "entry_price": 100, "exit_price": 110,
        "fees": 2, "stop_loss": 95,
    }
    short_trade = {
        "side": "short", "quantity": 2, "entry_price": 100, "exit_price": 90,
        "fees": 2, "stop_loss": 105,
    }
    assert trade_metrics(long_trade) == {
        "gross_pnl": 20.0, "net_pnl": 18.0, "return_pct": 10.0, "r_multiple": 1.8,
    }
    assert trade_metrics(short_trade)["net_pnl"] == 18.0


def test_open_trade_metrics_are_unavailable():
    result = trade_metrics({"side": "long", "quantity": 1, "entry_price": 10, "exit_price": None})
    assert result == {"gross_pnl": None, "net_pnl": None, "return_pct": None, "r_multiple": None}
