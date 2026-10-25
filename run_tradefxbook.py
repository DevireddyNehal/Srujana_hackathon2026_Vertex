#!/usr/bin/env python3
"""
Convenience entry point to run the TradeFXBook Trading Journal and Analytics platform.

Usage:
    python3 run_tradefxbook.py [--host 0.0.0.0] [--port 8080] [--seed]
"""

import argparse
import sys
import uvicorn
from tradefxbook.config import settings
from tradefxbook.generator import seed_demo_dataset, check_demo_dataset_status
from tradefxbook.verify import verify_dataset


def main():
    parser = argparse.ArgumentParser(description="TradeFXBook - Trading Journal & Analytics Platform")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--seed", action="store_true", help="Ensure 100,000 demo trades are seeded before launching")
    parser.add_argument("--verify", action="store_true", help="Run database integrity verification")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    if args.seed:
        print("[*] Checking / Seeding demo dataset...")
        seed_demo_dataset()

    if args.verify:
        verify_dataset(verbose=True)

    status = check_demo_dataset_status()
    if not status["is_complete"]:
        print("[!] Note: Demo dataset is not yet seeded. Auto-seeding 10 demo traders and 100,000 trades now...")
        seed_demo_dataset()
        print("[+] Seed complete.")

    print(f"\n================================================================================")
    print(f"  TRADEFXBOOK TRADING JOURNAL & ANALYTICS RUNNING")
    print(f"================================================================================")
    print(f"  Web Dashboard:  http://localhost:{args.port}/")
    print(f"  REST API Docs:  http://localhost:{args.port}/docs")
    print(f"  OpenAPI Schema: http://localhost:{args.port}/openapi.json")
    print(f"================================================================================\n")

    uvicorn.run("tradefxbook.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
