"""
TradeFXBook Command-Line Interface (CLI).
Provides commands to seed, verify, reset, and serve the application.

Usage:
    python3 -m tradefxbook.cli seed [--force]
    python3 -m tradefxbook.cli verify
    python3 -m tradefxbook.cli reset --confirm
    python3 -m tradefxbook.cli serve [--host 0.0.0.0] [--port 8080]
"""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tradefxbook.config import settings
from tradefxbook.generator import seed_demo_dataset, reset_demo_data
from tradefxbook.verify import verify_dataset


def main():
    parser = argparse.ArgumentParser(
        description="TradeFXBook - Professional Trading Journal & Analytics CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: seed
    seed_parser = subparsers.add_parser("seed", help="Seed 10 demo users and 100,000 closed demo trades")
    seed_parser.add_argument("--force", action="store_true", help="Force reseed even if data already exists")
    seed_parser.add_argument("--seed", type=int, default=settings.RANDOM_SEED, help="Random seed for reproducibility")

    # Command: verify
    verify_parser = subparsers.add_parser("verify", help="Verify exact counts and dataset integrity from DB")

    # Command: reset
    reset_parser = subparsers.add_parser("reset", help="Safely reset demo dataset preserving non-demo data")
    reset_parser.add_argument("--confirm", action="store_true", required=True, help="Explicit confirmation required")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI application server")
    serve_parser.add_argument("--host", default=settings.HOST, help="Host to bind server")
    serve_parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind server")
    serve_parser.add_argument("--reload", action="store_true", help="Enable live auto-reloading")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "seed":
        print(f"[*] Starting TradeFXBook demo data generation (Seed={args.seed}, Batch={settings.DEMO_SEED_BATCH})...")
        res = seed_demo_dataset(force_reseed=args.force, custom_seed=args.seed)
        print(f"[+] Status: {res.get('status')}")
        print(f"[+] Demo Users: {res.get('demo_users_count')}")
        print(f"[+] Total Seeded Trades: {res.get('demo_trades_count'):,}")
        print(f"[+] Total Closed Trades: {res.get('closed_demo_trades_count'):,}")
        print("[+] Now running verification...")
        verify_dataset(verbose=True)

    elif args.command == "verify":
        res = verify_dataset(verbose=True)
        sys.exit(0 if res["all_passed"] else 1)

    elif args.command == "reset":
        if not args.confirm:
            print("[!] Error: You must supply --confirm to reset the demo dataset.")
            sys.exit(1)
        print("[*] Performing safe demo reset...")
        res = reset_demo_data()
        print(f"[+] {res['status']}")
        print(f"[+] Deleted Demo Users: {res['deleted_demo_users']}")
        print(f"[+] Deleted Demo Trades: {res['deleted_demo_trades']}")

    elif args.command == "serve":
        import uvicorn
        print(f"[*] Launching TradeFXBook Trading Journal on http://{args.host}:{args.port} ...")
        uvicorn.run("tradefxbook.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
