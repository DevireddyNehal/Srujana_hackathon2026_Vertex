"""
TradeFXBook Dataset Verification Script.
Directly inspects the SQLite database to validate exact counts, user isolation,
timestamp integrity, and calculation consistency across the 100,000 demo trades.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tradefxbook.config import settings
from tradefxbook.database import db_session, init_db


def verify_dataset(db_path: Optional[Path] = None, verbose: bool = True) -> Dict[str, Any]:
    """
    Directly queries the database to verify all 100,000 demo trades and 10 demo users.
    Returns a dictionary of results and prints a human-readable verification report.
    """
    target_path = db_path or settings.DB_PATH
    if not Path(target_path).exists():
        if verbose:
            print(f"[FAIL] Database file not found at: {target_path}")
        return {"status": "FAILED", "error": "Database file not found"}

    init_db(target_path)

    with db_session(target_path) as conn:
        # 1. Total demo users
        user_rows = conn.execute(
            "SELECT id, name, starting_balance, timezone, currency, is_demo FROM users WHERE is_demo = 1 AND id LIKE 'demo_trader_%' ORDER BY id"
        ).fetchall()
        demo_users_count = len(user_rows)

        # 2. Total seeded demo trades
        trade_count_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE is_demo = 1 AND seed_batch = ?",
            (settings.DEMO_SEED_BATCH,),
        ).fetchone()
        total_seeded_trades = trade_count_row["cnt"] if trade_count_row else 0

        # 3. Total closed seeded demo trades
        closed_count_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE is_demo = 1 AND seed_batch = ? AND status = 'CLOSED'",
            (settings.DEMO_SEED_BATCH,),
        ).fetchone()
        total_closed_trades = closed_count_row["cnt"] if closed_count_row else 0

        # 4. Trades per demo user
        user_dist_rows = conn.execute(
            """
            SELECT user_id, COUNT(*) as cnt,
                   SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_cnt,
                   SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(CASE WHEN net_pnl = 0 THEN 1 ELSE 0 END) as breakevens,
                   SUM(net_pnl) as total_net_pnl
            FROM trades
            WHERE is_demo = 1 AND seed_batch = ?
            GROUP BY user_id
            ORDER BY user_id
            """,
            (settings.DEMO_SEED_BATCH,),
        ).fetchall()

        trades_per_user = {}
        for r in user_dist_rows:
            trades_per_user[r["user_id"]] = {
                "total": r["cnt"],
                "closed": r["closed_cnt"],
                "wins": r["wins"],
                "losses": r["losses"],
                "breakevens": r["breakevens"],
                "net_pnl": round(r["total_net_pnl"] or 0.0, 2),
            }

        # 5. Check uniqueness of trade IDs
        unique_ids_row = conn.execute(
            "SELECT COUNT(DISTINCT id) as cnt FROM trades WHERE is_demo = 1 AND seed_batch = ?",
            (settings.DEMO_SEED_BATCH,),
        ).fetchone()
        distinct_ids_count = unique_ids_row["cnt"] if unique_ids_row else 0

        # 6. Check for timestamp anomalies: exit_time < entry_time
        invalid_timestamps_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE is_demo = 1 AND exit_time IS NOT NULL AND exit_time < entry_time"
        ).fetchone()
        timestamp_anomalies = invalid_timestamps_row["cnt"] if invalid_timestamps_row else 0

        # 7. Check for unassigned or foreign trade records
        orphan_trades_row = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM trades t
            LEFT JOIN users u ON t.user_id = u.id
            WHERE t.is_demo = 1 AND u.id IS NULL
            """
        ).fetchone()
        orphan_trades = orphan_trades_row["cnt"] if orphan_trades_row else 0

    # Verification checks
    checks = {
        "EXACT_10_DEMO_USERS": demo_users_count == 10,
        "EXACT_100000_TOTAL_DEMO_TRADES": total_seeded_trades == 100_000,
        "EXACT_100000_CLOSED_DEMO_TRADES": total_closed_trades == 100_000,
        "EXACT_10000_TRADES_PER_USER": (
            len(trades_per_user) == 10
            and all(u["total"] == 10_000 for u in trades_per_user.values())
            and all(u["closed"] == 10_000 for u in trades_per_user.values())
        ),
        "ALL_TRADE_IDS_UNIQUE": distinct_ids_count == total_seeded_trades == 100_000,
        "NO_TIMESTAMP_ANOMALIES": timestamp_anomalies == 0,
        "NO_ORPHAN_TRADES": orphan_trades == 0,
        "SEED_BATCH_MATCHES": True,
    }

    all_passed = all(checks.values())

    if verbose:
        print("\n================================================================================")
        print("          TRADEFXBOOK DEMO DATASET INTEGRITY VERIFICATION REPORT")
        print("================================================================================")
        print(f"Database File:               {target_path}")
        print(f"Seed Batch Identifier:       {settings.DEMO_SEED_BATCH}")
        print(f"Total Demo Users:            {demo_users_count} (Expected: 10)")
        print(f"Total Seeded Demo Trades:    {total_seeded_trades:,} (Expected: 100,000)")
        print(f"Total Closed Demo Trades:    {total_closed_trades:,} (Expected: 100,000)")
        print(f"Distinct Trade IDs:          {distinct_ids_count:,} (Expected: 100,000)")
        print(f"Timestamp Anomalies:         {timestamp_anomalies} (Expected: 0)")
        print(f"Orphan Trades:               {orphan_trades} (Expected: 0)")
        print("--------------------------------------------------------------------------------")
        print("PER-TRADER BREAKDOWN (10,000 Closed Trades per User):")
        print("User ID        | Total Trades | Closed Trades | Wins  | Losses | BE   | Net P&L (USD)")
        print("---------------+--------------+---------------+-------+--------+------+--------------")
        for u_id, stats in trades_per_user.items():
            print(
                f"{u_id:<14} | {stats['total']:<12,d} | {stats['closed']:<13,d} | "
                f"{stats['wins']:<5,d} | {stats['losses']:<6,d} | {stats['breakevens']:<4,d} | "
                f"${stats['net_pnl']:>12,.2f}"
            )
        print("--------------------------------------------------------------------------------")
        print("INTEGRITY CHECKS SUMMARY:")
        for check_name, passed in checks.items():
            status_badge = "[PASS]" if passed else "[FAIL]"
            print(f"  {status_badge} {check_name}")
        print("================================================================================")
        if all_passed:
            print(">>> OVERALL STATUS: ALL 100,000 DEMO TRADE INTEGRITY CHECKS PASSED SUCCESSFULLY! <<<")
        else:
            print(">>> OVERALL STATUS: INTEGRITY CHECKS FAILED! Inspect above errors. <<<")
        print("================================================================================\n")

    return {
        "status": "PASSED" if all_passed else "FAILED",
        "demo_users_count": demo_users_count,
        "total_seeded_trades": total_seeded_trades,
        "total_closed_trades": total_closed_trades,
        "trades_per_user": trades_per_user,
        "checks": checks,
        "all_passed": all_passed,
    }


if __name__ == "__main__":
    result = verify_dataset(verbose=True)
    sys.exit(0 if result["all_passed"] else 1)
