"""Statistics + Daily P&L. Every number is derived from closed trades (status='closed') grouped by
CLOSING date in the account's time zone. Open-trade P&L is never included."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
MAX_SPAN = 3700
W = "user_id=? AND status='closed' AND closed_date BETWEEN ? AND ?"


class NotFound(Exception):
    pass


def get_account(conn, user_id):
    r = conn.execute("SELECT * FROM accounts WHERE user_id=?", (user_id,)).fetchone()
    if not r:
        raise NotFound(f"unknown account '{user_id}'")
    return dict(r)


def as_of(a):
    return date.fromisoformat(a["data_end"]) if a["data_end"] else datetime.now(ZoneInfo(a["tz"])).date()


def resolve_range(conn, a, key="90d", start=None, end=None):
    asof = as_of(a)
    if key in RANGE_DAYS:
        s, e = asof - timedelta(days=RANGE_DAYS[key] - 1), asof
    elif key == "ytd":
        s, e = date(asof.year, 1, 1), asof
    elif key == "all":
        m = conn.execute("SELECT MIN(closed_date) m FROM trades WHERE user_id=? AND status='closed'",
                         (a["user_id"],)).fetchone()["m"]
        s, e = (date.fromisoformat(m) if m else asof), asof
    elif key == "custom":
        if not start or not end:
            raise ValueError("custom range requires start and end (YYYY-MM-DD)")
        try:
            s, e = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError as exc:
            raise ValueError("dates must use YYYY-MM-DD format") from exc
        if s.isoformat() != start or e.isoformat() != end:
            raise ValueError("dates must use YYYY-MM-DD format")
    else:
        raise ValueError(f"unknown range '{key}'")
    if key != "custom" and (start is not None or end is not None):
        raise ValueError("start and end may only be supplied with range=custom")
    if s > e:
        raise ValueError("start must be on or before end")
    if e > asof:
        raise ValueError("end cannot be after the account's latest data date")
    if (e - s).days + 1 > MAX_SPAN:
        raise ValueError("range too long")
    return s, e


def _where(session):
    return W + (" AND session=?" if session != "all" else "")


def _p(a, s, e, session="all"):
    params = (a["user_id"], s.isoformat(), e.isoformat())
    return (*params, session) if session != "all" else params


def _pct(x, y):
    return round(x / y * 100, 2) if y else None


def max_drawdown(start_equity, nets):
    """Peak-to-trough on the closed-trade equity curve (realized only, no intratrade drawdown)."""
    eq = peak = start_equity
    mdd = mdd_pct = 0.0
    for x in nets:
        eq += x
        peak = max(peak, eq)
        dd = peak - eq
        mdd = max(mdd, dd)
        if peak > 0:
            mdd_pct = max(mdd_pct, dd / peak * 100)
    return round(mdd, 2), round(mdd_pct, 2)


def daily_pnl(conn, a, s, e, session="all"):
    rows = {r["d"]: (r["net"], r["n"]) for r in conn.execute(
        f"SELECT closed_date d, SUM(net) net, COUNT(*) n FROM trades WHERE {_where(session)} GROUP BY closed_date",
        _p(a, s, e, session))}
    days, cum = [], 0.0
    for i in range((e - s).days + 1):
        d = (s + timedelta(i)).isoformat()
        net, n = rows.get(d, (0.0, 0))
        net = round(net, 2)
        cum = round(cum + net, 2)
        days.append({"date": d, "net_pnl": net, "trades": n, "cumulative_pnl": cum})
    nets = [x["net_pnl"] for x in days]
    return {"currency": a["currency"], "timezone": a["tz"], "start": s.isoformat(), "end": e.isoformat(),
            "days": days,
            "totals": {"net_pnl": cum, "closed_trades": sum(x["trades"] for x in days),
                       "calendar_days": len(days), "profitable_days": sum(v > 0 for v in nets),
                       "losing_days": sum(v < 0 for v in nets), "flat_days": sum(v == 0 for v in nets),
                       "best_day": max(days, key=lambda x: x["net_pnl"]) if days else None,
                       "worst_day": min(days, key=lambda x: x["net_pnl"]) if days else None}}


def breakdown(conn, a, s, e, by, session="all"):
    col = {"setup": "setup", "session": "session", "symbol": "instrument"}[by]
    out = []
    for r in conn.execute(f"""SELECT COALESCE({col},'Untagged') k, COUNT(*) n, SUM(net>0) w, SUM(net<0) l,
        COALESCE(SUM(net),0) net, COALESCE(SUM(CASE WHEN net>0 THEN net END),0) pos,
        COALESCE(SUM(CASE WHEN net<0 THEN net END),0) neg FROM trades
        WHERE {_where(session)} GROUP BY k ORDER BY net DESC""", _p(a, s, e, session)):
        out.append({"name": r["k"], "trades": r["n"], "net_pnl": round(r["net"], 2),
                    "win_rate": _pct(r["w"] or 0, r["n"]),
                    "profit_factor": round(r["pos"] / -r["neg"], 2) if r["neg"] < 0 else None})
    return out


def overview(conn, user_id, key="90d", start=None, end=None, session="all"):
    a = get_account(conn, user_id)
    s, e = resolve_range(conn, a, key, start, end)
    p = _p(a, s, e, session)
    where = _where(session)
    r = conn.execute(f"""SELECT COUNT(*) n, COALESCE(SUM(net>0),0) w, COALESCE(SUM(net<0),0) l,
        COALESCE(SUM(net=0),0) b, COALESCE(SUM(CASE WHEN net>0 THEN net END),0) pos,
        COALESCE(SUM(CASE WHEN net<0 THEN net END),0) neg, COALESCE(SUM(net),0) total,
        COALESCE(SUM(gross),0) gross, COALESCE(SUM(commission),0) comm, COALESCE(SUM(fees),0) fees,
        COALESCE(SUM(slippage),0) slip, COALESCE(SUM(swap),0) swap,
        COALESCE(SUM(rule_adhered IS NOT NULL),0) ev, COALESCE(SUM(rule_adhered=1),0) ok
        FROM trades WHERE {where}""", p).fetchone()
    n, w, l, b = r["n"], r["w"], r["l"], r["b"]
    pos, neg, total = round(r["pos"], 2), round(r["neg"], 2), round(r["total"], 2)
    pf, pf_reason = None, None
    if n == 0:
        pf_reason = "no_closed_trades"
    elif neg >= 0:
        pf_reason = "no_losing_trades"
    else:
        pf = round(pos / -neg, 2)
    avg_win = round(pos / w, 2) if w else None
    avg_loss = round(-neg / l, 2) if l else None
    opening_where = "user_id=? AND status='closed' AND closed_date<?"
    opening_params = (a["user_id"], s.isoformat())
    if session != "all":
        opening_where += " AND session=?"
        opening_params += (session,)
    opening = a["start_balance"] + conn.execute(
        f"SELECT COALESCE(SUM(net),0) FROM trades WHERE {opening_where}",
        opening_params).fetchone()[0]
    nets = [x[0] for x in conn.execute(f"SELECT net FROM trades WHERE {where} ORDER BY closed_at, id", p)]
    dd, dd_pct = max_drawdown(opening, nets)
    daily = daily_pnl(conn, a, s, e, session)
    active = [d for d in daily["days"] if d["trades"] > 0]
    wk, mo = {}, {}
    for d in active:
        dt = date.fromisoformat(d["date"])
        wk[dt.isocalendar()[:2]] = wk.get(dt.isocalendar()[:2], 0) + d["net_pnl"]
        mo[(dt.year, dt.month)] = mo.get((dt.year, dt.month), 0) + d["net_pnl"]
    span = len(daily["days"])
    costs = round(r["comm"] + r["fees"] + r["slip"] - r["swap"], 2)
    return {
        "account": {"user_id": a["user_id"], "name": a["name"], "currency": a["currency"],
                    "timezone": a["tz"], "is_demo": bool(a["is_demo"]), "start_balance": a["start_balance"]},
        "period": {"key": key, "start": s.isoformat(), "end": e.isoformat(), "calendar_days": span},
        "net_pnl": total, "closed_trades": n,
        "win_rate": {"value": _pct(w, n), "wins": w, "losses": l, "break_even": b},
        "profit_factor": {"value": pf, "unavailable_reason": pf_reason, "gross_profit": pos, "gross_loss": -neg},
        "expectancy": round(total / n, 2) if n else None,
        "max_drawdown": {"amount": dd, "percent": dd_pct, "opening_equity": round(opening, 2),
                         "basis": "realized closed-trade equity curve; amount and percent each maximised independently"},
        "avg_win_loss": {"avg_win": avg_win, "avg_loss": avg_loss,
                         "realized_reward_to_risk": round(avg_win / avg_loss, 2) if avg_win and avg_loss else None},
        "frequency": {"closed_trades": n, "per_calendar_day": round(n / span, 2),
                      "per_week": round(n / span * 7, 2), "per_month": round(n / span * 30.4375, 2),
                      "active_days": len(active)},
        "consistency": {"profitable_days": sum(d["net_pnl"] > 0 for d in active), "active_days": len(active),
                        "profitable_day_pct": _pct(sum(d["net_pnl"] > 0 for d in active), len(active)),
                        "profitable_weeks": sum(v > 0 for v in wk.values()), "active_weeks": len(wk),
                        "profitable_months": sum(v > 0 for v in mo.values()), "active_months": len(mo)},
        "rule_adherence": {"evaluated_trades": r["ev"], "adhered": r["ok"],
                           "percent": _pct(r["ok"], r["ev"]) if r["ev"] else None},
        "costs": {"gross_pnl": round(r["gross"], 2), "commission": round(r["comm"], 2), "fees": round(r["fees"], 2),
                  "slippage": round(r["slip"], 2), "swap_signed": round(r["swap"], 2), "total_costs": costs,
                  "net_pnl": total,
                  "slippage_source": "simulated (demo data)" if a["is_demo"] else "as recorded"},
        "setups": breakdown(conn, a, s, e, "setup", session),
        "sessions": breakdown(conn, a, s, e, "session", session),
        "symbols": breakdown(conn, a, s, e, "symbol", session),
        "daily_pnl": daily,
        "disclaimer": "Historical trading performance is descriptive and does not predict future results.",
    }


def list_accounts(conn):
    return [dict(r) for r in conn.execute(
        "SELECT user_id, name, currency, tz, is_demo FROM accounts WHERE is_demo=1 ORDER BY user_id")]
