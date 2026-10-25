"""Reproducible synthetic demo data. Trades are generated first; every metric is derived later.
Usage: python -m trading_stats.generator --db trading.db
"""
import argparse, math, os, random
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from . import db

SEED, REF_END, N_TRADERS, N_TRADES, YEARS = 20261023, date(2026, 10, 23), 10, 10000, 3
# symbol: (reference price, contract size, price decimals, typical adverse move in price units)
# All USD-quoted, so gross P&L = (exit-entry) * direction * qty * contract_size is in USD.
INSTR = {"EURUSD": (1.08, 100000, 5, .0030), "GBPUSD": (1.27, 100000, 5, .0040),
         "AUDUSD": (.66, 100000, 5, .0025), "NZDUSD": (.61, 100000, 5, .0025),
         "XAUUSD": (2300, 100, 2, 18.0), "US30": (38000, 1, 1, 220.0)}
SETUPS = ["Breakout", "Pullback", "Range Fade", "News Momentum", "Trend Continuation", "Reversal"]
TZS = ["America/New_York", "Europe/London", "Asia/Kolkata", "Australia/Sydney"]
UTC = timezone.utc


def gen_trader(idx, n, end, seed, years=YEARS):
    rng = random.Random(f"{seed}-{idx}")
    uid = f"demo_{idx:02d}"
    bal = rng.choice([25000, 50000, 100000, 150000, 250000])
    scale = bal / 100000
    base_p, R = rng.uniform(.42, .56), rng.uniform(1.2, 1.9)
    tilt = {s: rng.uniform(-.08, .08) for s in SETUPS}
    start = end - timedelta(days=365 * years)
    days = [start + timedelta(i) for i in range((end - start).days + 1)
            if (start + timedelta(i)).weekday() < 5]
    w = [rng.lognormvariate(0, .5) for _ in days]
    for _ in range(7):  # quiet periods
        i, ln = rng.randrange(len(days)), rng.randint(8, 20)
        for j in range(i, min(i + ln, len(days))):
            w[j] *= .05
    slots = []
    for di in rng.choices(range(len(days)), weights=w, k=n):
        r = rng.random()
        hr = rng.randint(0, 6) if r < .2 else rng.randint(7, 12) if r < .6 else rng.randint(13, 20)
        slots.append((days[di], hr, rng.randrange(60), rng.randrange(60)))
    slots.sort()
    rows, regime, left = [], 0.0, rng.randint(150, 400)
    for i, (d, h, m, s) in enumerate(slots):
        if left == 0:  # hot/cold regimes create streaks, drawdowns and recoveries
            regime, left = rng.choice([-.12, 0, 0, .08]), rng.randint(150, 400)
        left -= 1
        sym = rng.choice(list(INSTR))
        px, cs, dec, sd = INSTR[sym]
        setup = rng.choice(SETUPS)
        adhered = rng.random() < .82
        rule = None if rng.random() < .10 else int(adhered)
        p = min(.85, max(.15, base_p + regime + tilt[setup] - (0 if adhered else .07)))
        dirn = rng.choice((1, -1))
        qty = round(max(.01, rng.lognormvariate(math.log(.4 * scale), .5)), 2)
        entry = round(px * rng.uniform(.94, 1.06), dec)
        opened = datetime(d.year, d.month, d.day, h, m, s, tzinfo=UTC)
        close = opened + timedelta(minutes=max(1, min(int(rng.lognormvariate(math.log(75), 1.1)), 2880)))
        if close.weekday() >= 5 or close.date() > end:
            close = opened + timedelta(minutes=rng.randint(5, 60))
        scratch, win = rng.random() < .025, rng.random() < p
        loss_mag = sd * rng.uniform(.5, 1.3)
        mag = loss_mag * R * rng.uniform(.6, 1.5) if win else loss_mag
        mag *= 4 if rng.random() < .01 else 1  # outliers
        exit_ = entry if scratch else round(entry + dirn * (mag if win else -mag), dec)
        gross = round((exit_ - entry) * dirn * qty * cs, 2)  # consistent with entry/exit/qty
        if scratch:  # true break-even: exit == entry, commissions waived
            comm = fees = slip = swap = 0.0
        else:
            nights = (close.date() - opened.date()).days
            comm, fees = round(qty * rng.uniform(5, 8), 2), round(qty * rng.uniform(.2, .8), 2)
            slip = round(qty * rng.uniform(0, 2.5), 2)  # SIMULATED, not measured from fills
            swap = round(qty * nights * rng.uniform(-3.5, 1), 2)
        rows.append(dict(id=f"{uid}-{i+1:05d}", user_id=uid, instrument=sym, direction=dirn,
                         qty=qty, entry=entry, exit=exit_, contract_size=cs, opened_at=opened,
                         closed_at=close, setup=setup, gross=gross, commission=comm, fees=fees,
                         slippage=slip, swap=swap, rule_adhered=rule))
    acct = dict(user_id=uid, name=f"DEMO Trader {idx:02d} (synthetic)", currency="USD",
                start_balance=float(bal), tz=TZS[(idx - 1) % len(TZS)], is_demo=1, data_end=end.isoformat())
    z = ZoneInfo(acct["tz"])  # data_end = latest LOCAL closing date, so "all history" covers every trade
    acct["data_end"] = max(r["closed_at"].astimezone(z).date() for r in rows).isoformat()
    return acct, rows


def seed(conn, traders=N_TRADERS, trades=N_TRADES, end=REF_END, seed_=SEED):
    if os.environ.get("APP_ENV", "").lower() == "production":
        raise RuntimeError("Demo seeding is disabled when APP_ENV=production")
    db.init_db(conn)
    with conn:  # one transaction; rerun replaces demo rows only
        for idx in range(1, traders + 1):
            acct, rows = gen_trader(idx, trades, end, seed_)
            ex = conn.execute("SELECT is_demo FROM accounts WHERE user_id=?", (acct["user_id"],)).fetchone()
            if ex and not ex["is_demo"]:
                raise RuntimeError(f"{acct['user_id']} is a real account; refusing to touch it")
            conn.execute("DELETE FROM trades WHERE user_id=? AND is_demo=1", (acct["user_id"],))
            conn.execute("INSERT OR REPLACE INTO accounts VALUES(:user_id,:name,:currency,:start_balance,:tz,:is_demo,:data_end)", acct)
            db.insert_trades(conn, rows, acct["tz"], True)
    return conn.execute("SELECT COUNT(*) FROM trades WHERE is_demo=1").fetchone()[0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("TRADING_DB", "trading.db"))
    ap.add_argument("--traders", type=int, default=N_TRADERS)
    ap.add_argument("--trades", type=int, default=N_TRADES)
    ap.add_argument("--end", default=REF_END.isoformat())
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    c = db.connect(a.db)
    print("demo trades in database:", seed(c, a.traders, a.trades, date.fromisoformat(a.end), a.seed))
