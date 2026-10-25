#!/usr/bin/env python3
"""Construct the wide close-price and daily-return tables from the raw NSE history export.

The repository contains the canonical long-form source at
``f06_historical_dataset/historical_prices.csv``. This script rebuilds the derived
wide-price matrix and the return series without fabricating missing values.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "f06_historical_dataset"
SOURCE_FILE = DATA_DIR / "historical_prices.csv"


def _build_close_wide(prices: pd.DataFrame) -> pd.DataFrame:
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prices = prices.dropna(subset=["date", "ticker"]).sort_values(["date", "ticker"], kind="stable")

    selected: dict[str, pd.Series] = {}
    for ticker, group in prices.groupby("ticker", sort=True):
        group = group.sort_values("date")
        if group["adjusted_close"].notna().any():
            series = group.set_index("date")["adjusted_close"].astype(float)
        elif group["close"].notna().any():
            series = group.set_index("date")["close"].astype(float)
        else:
            series = pd.Series(dtype=float)
        selected[ticker] = series

    dates = pd.Index(sorted(prices["date"].dropna().unique()))
    date_index = pd.to_datetime(dates)
    wide = pd.DataFrame(index=date_index)
    wide.index.name = "date"

    for ticker in sorted(selected):
        series = selected[ticker]
        if series.empty:
            wide[ticker] = pd.NA
            continue
        series.index = pd.to_datetime(series.index)
        wide[ticker] = series.reindex(date_index).to_numpy()

    wide = wide.reset_index()
    wide.columns = ["date"] + [str(col) for col in wide.columns[1:]]
    wide["date"] = wide["date"].dt.strftime("%Y-%m-%d")
    return wide


def _build_daily_returns(close_wide: pd.DataFrame) -> pd.DataFrame:
    frame = close_wide.set_index("date").copy()
    returns = frame.pct_change(fill_method=None).reset_index()
    returns["date"] = pd.to_datetime(returns["date"]).dt.strftime("%Y-%m-%d")
    return returns


def main() -> int:
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Source file not found: {SOURCE_FILE}")

    prices = pd.read_csv(SOURCE_FILE)
    close_wide = _build_close_wide(prices)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    close_wide_path = DATA_DIR / "close_wide.csv"
    close_wide.to_csv(close_wide_path, index=False, float_format="%.8f", na_rep="")

    adjusted_close_path = DATA_DIR / "adjusted_close_wide.csv"
    if adjusted_close_path.exists():
        close_wide.to_csv(adjusted_close_path, index=False, float_format="%.8f", na_rep="")

    returns = _build_daily_returns(close_wide)
    returns_path = DATA_DIR / "daily_Return.csv"
    returns.to_csv(returns_path, index=False, float_format="%.8f", na_rep="")

    canonical_returns_path = DATA_DIR / "daily_returns.csv"
    if canonical_returns_path.exists():
        returns.to_csv(canonical_returns_path, index=False, float_format="%.8f", na_rep="")

    print(f"Wrote {close_wide_path}")
    print(f"Wrote {returns_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
