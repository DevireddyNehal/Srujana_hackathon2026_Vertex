from backend.journal.analytics import analyze_trades


def test_analytics_computes_wins_drawdown_and_groupings():
    trades = [
        {"id": "1", "closed_at": "2026-01-01T12:00:00+00:00", "net_pnl": 100, "r_multiple": 1.0,
         "symbol": "ABC", "strategy": "breakout"},
        {"id": "2", "closed_at": "2026-01-02T12:00:00+00:00", "net_pnl": -40, "r_multiple": -0.4,
         "symbol": "ABC", "strategy": "breakout"},
        {"id": "3", "closed_at": "2026-02-01T12:00:00+00:00", "net_pnl": 60, "r_multiple": 0.6,
         "symbol": "XYZ", "strategy": "reversal"},
    ]
    result = analyze_trades(trades)
    assert result["summary"]["trade_count"] == 3
    assert result["summary"]["win_rate_pct"] == 66.67
    assert result["summary"]["net_pnl"] == 120
    assert result["summary"]["max_drawdown"] == 40
    assert len(result["monthly_pnl"]) == 2
