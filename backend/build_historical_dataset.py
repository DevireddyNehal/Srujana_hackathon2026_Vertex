#!/usr/bin/env python3
"""Build a reproducible, non-fabricated F-06 daily Indian-market dataset.

Fetches historical daily bars from Yahoo Finance's chart endpoint and writes:
  historical_prices.csv           Long-form raw observations; no synthetic rows
  corporate_actions.csv           Dividends/splits returned by the source
  missing_observations.csv        Missing asset bars relative to observed market sessions
  duplicate_rows.csv              Duplicate date/ticker records, if any
  data_quality_summary.csv        Per-asset coverage/null/validation summary
  adjusted_close_wide.csv          Wide selected price series; missing values stay blank
  daily_returns.csv                Daily returns from the selected field; no fill-forward
  historical_metrics.csv           Return/volatility/drawdown metrics derived from observations
  metadata.json                    Source, retrieval timestamp, mapping and limitations
  README.md                        Dataset interpretation and reproducibility notes

No missing prices are imputed. If a source asset fails to download, the partial result is
marked explicitly in metadata and reports; the script does not silently claim completeness.
"""
from __future__ import annotations

import json
import math
import sys
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

SOURCE_NAME = "Yahoo Finance Chart endpoint (unofficial endpoint; see README limitations)"
SOURCE_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

ASSETS: dict[str, dict[str, str]] = {
    "TCS.NS": {
        "asset_name": "Tata Consultancy Services Limited",
        "exchange": "NSE India",
        "asset_type": "Equity",
        "currency": "INR",
        "symbol_note": "Yahoo Finance symbol for NSE-listed TCS.",
    },
    "INFY.NS": {
        "asset_name": "Infosys Limited",
        "exchange": "NSE India",
        "asset_type": "Equity",
        "currency": "INR",
        "symbol_note": "Yahoo Finance symbol for NSE-listed Infosys.",
    },
    "HDFCBANK.NS": {
        "asset_name": "HDFC Bank Limited",
        "exchange": "NSE India",
        "asset_type": "Equity",
        "currency": "INR",
        "symbol_note": "Yahoo Finance symbol for NSE-listed HDFC Bank.",
    },
    "^NSEI": {
        "asset_name": "NIFTY 50 Index",
        "exchange": "NSE Indices",
        "asset_type": "Equity index (price index)",
        "currency": "INR",
        "symbol_note": "Yahoo Finance symbol for NIFTY 50; generally no adjusted close or traded volume.",
    },
    "GOLDBEES.NS": {
        "asset_name": "Nippon India ETF Gold BeES",
        "exchange": "NSE India",
        "asset_type": "Gold ETF",
        "currency": "INR",
        "symbol_note": "Yahoo Finance symbol for Gold BeES ETF.",
    },
    "LIQUIDBEES.NS": {
        "asset_name": "Nippon India ETF Liquid BeES",
        "exchange": "NSE India",
        "asset_type": "Liquid debt ETF",
        "currency": "INR",
        "symbol_note": "Yahoo Finance symbol for Liquid BeES ETF.",
    },
}
PRICE_COLUMNS = [
    "date", "ticker", "open", "high", "low", "close", "adjusted_close", "volume", "currency"
]
NUMERIC_COLUMNS = ["open", "high", "low", "close", "adjusted_close", "volume"]


def date_minus_years(d: date, years: int) -> date:
    """Subtract calendar years while safely handling leap day."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(year=d.year - years, month=2, day=28)


def _unix_at_utc_midnight(d: date) -> int:
    return int(datetime.combine(d, dt_time.min, tzinfo=UTC).timestamp())


def _session_date_from_timestamp(timestamp: int | float) -> str:
    # Yahoo daily-bar timestamps are converted to the Indian session date.
    return datetime.fromtimestamp(float(timestamp), tz=UTC).astimezone(IST).date().isoformat()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _as_volume(value: Any) -> int | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return int(v)


def fetch_symbol(
    session: requests.Session, ticker: str, start_date: date, end_date: date, retries: int = 3
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Fetch bars and source-reported corporate-action events for one symbol."""
    url = SOURCE_BASE + quote(ticker, safe=".")
    params = {
        "period1": _unix_at_utc_midnight(start_date),
        # Yahoo's period2 is exclusive, so the requested end date must be followed by one day.
        "period2": _unix_at_utc_midnight(end_date + timedelta(days=1)),
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    last_error: str | None = None
    payload: dict[str, Any] | None = None
    for attempt in range(retries):
        try:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    if payload is None:
        raise RuntimeError(last_error or "Unknown request failure")

    chart = payload.get("chart", {})
    if chart.get("error"):
        err = chart["error"]
        raise RuntimeError(f"Yahoo chart error: {err.get('code')}: {err.get('description')}")
    results = chart.get("result") or []
    if not results:
        raise RuntimeError("Yahoo Finance returned no historical chart result")

    result = results[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quote_rows = (indicators.get("quote") or [{}])[0]
    adj_rows = (indicators.get("adjclose") or [{}])[0]
    adj_values = adj_rows.get("adjclose") or []
    bars: list[dict[str, Any]] = []

    fields = {
        "open": quote_rows.get("open") or [],
        "high": quote_rows.get("high") or [],
        "low": quote_rows.get("low") or [],
        "close": quote_rows.get("close") or [],
        "volume": quote_rows.get("volume") or [],
    }
    for i, ts in enumerate(timestamps):
        session_date = _session_date_from_timestamp(ts)
        if session_date < start_date.isoformat() or session_date > end_date.isoformat():
            continue
        row = {
            "date": session_date,
            "ticker": ticker,
            "open": _as_float(fields["open"][i]) if i < len(fields["open"]) else None,
            "high": _as_float(fields["high"][i]) if i < len(fields["high"]) else None,
            "low": _as_float(fields["low"][i]) if i < len(fields["low"]) else None,
            "close": _as_float(fields["close"][i]) if i < len(fields["close"]) else None,
            "adjusted_close": _as_float(adj_values[i]) if i < len(adj_values) else None,
            "volume": _as_volume(fields["volume"][i]) if i < len(fields["volume"]) else None,
            "currency": ASSETS[ticker]["currency"],
        }
        bars.append(row)

    actions: list[dict[str, Any]] = []
    events = result.get("events") or {}
    for action_type in ("dividends", "splits"):
        for ts_key, event in (events.get(action_type) or {}).items():
            try:
                event_ts = event.get("date", int(ts_key))
                event_date = _session_date_from_timestamp(event_ts)
            except (TypeError, ValueError):
                event_date = str(ts_key)
            if event_date < start_date.isoformat() or event_date > end_date.isoformat():
                continue
            actions.append({
                "date": event_date,
                "ticker": ticker,
                "action_type": "dividend" if action_type == "dividends" else "split",
                "dividend_amount": _as_float(event.get("amount")) if action_type == "dividends" else None,
                "split_numerator": _as_float(event.get("numerator")) if action_type == "splits" else None,
                "split_denominator": _as_float(event.get("denominator")) if action_type == "splits" else None,
                "split_ratio": _as_float(event.get("numerator")) / _as_float(event.get("denominator"))
                    if action_type == "splits" and _as_float(event.get("denominator")) not in (None, 0)
                    and _as_float(event.get("numerator")) is not None else None,
                "currency": ASSETS[ticker]["currency"],
                "source_event_type": action_type,
            })

    source_meta = result.get("meta") or {}
    info = {
        "ticker": ticker,
        "source_url": response.url if 'response' in locals() else url,
        "source_currency": source_meta.get("currency"),
        "source_exchange_name": source_meta.get("fullExchangeName"),
        "source_symbol": source_meta.get("symbol"),
        "source_timezone": (source_meta.get("exchangeTimezoneName") or source_meta.get("timezone")),
        "source_first_bar_epoch": min(timestamps) if timestamps else None,
        "source_last_bar_epoch": max(timestamps) if timestamps else None,
    }
    return bars, actions, info


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, na_rep="", date_format="%Y-%m-%d", float_format="%.8f", encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Download and validate F-06 daily market history.")
    parser.add_argument("--start", help="Inclusive start date YYYY-MM-DD (default: 3 calendar years before today)")
    parser.add_argument("--end", help="Inclusive end date YYYY-MM-DD (default: today)")
    parser.add_argument("--out", default="f06_historical_dataset", help="Output directory")
    args = parser.parse_args()

    today = datetime.now(IST).date()
    try:
        start_date = date.fromisoformat(args.start) if args.start else date_minus_years(today, 3)
        end_date = date.fromisoformat(args.end) if args.end else today
    except ValueError as exc:
        parser.error(f"Dates must use YYYY-MM-DD: {exc}")
    if start_date > end_date:
        parser.error("--start must be on or before --end")

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    retrieval_time = datetime.now(UTC).isoformat(timespec="seconds")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; F06-Historical-Dataset-Builder/1.0; educational research)",
        "Accept": "application/json,text/plain,*/*",
    })

    all_bars: list[dict[str, Any]] = []
    all_actions: list[dict[str, Any]] = []
    per_symbol_info: dict[str, dict[str, Any]] = {}
    fetch_errors: dict[str, str] = {}

    print(f"Fetching daily observations {start_date} through {end_date} (inclusive)...")
    for ticker in ASSETS:
        try:
            bars, actions, info = fetch_symbol(session, ticker, start_date, end_date)
            if not bars:
                raise RuntimeError("The source returned no daily bars for the requested period")
            all_bars.extend(bars)
            all_actions.extend(actions)
            per_symbol_info[ticker] = info
            print(f"  OK  {ticker}: {len(bars)} bars, {len(actions)} corporate-action events")
        except Exception as exc:  # record the specific asset failure rather than hide it
            fetch_errors[ticker] = f"{type(exc).__name__}: {exc}"
            per_symbol_info[ticker] = {"ticker": ticker, "fetch_status": "FAILED", "fetch_error": fetch_errors[ticker]}
            print(f"  FAIL {ticker}: {fetch_errors[ticker]}", file=sys.stderr)

    if not all_bars:
        print("No real observations were downloaded; no historical price file was created.", file=sys.stderr)
        return 2

    prices = pd.DataFrame(all_bars, columns=PRICE_COLUMNS)
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prices = prices.sort_values(["date", "ticker"], kind="stable").reset_index(drop=True)

    # Preserve a duplicate diagnostic before deduplication. Conflicting duplicate keys stop the build.
    duplicate_mask = prices.duplicated(subset=["date", "ticker"], keep=False)
    duplicate_rows = prices.loc[duplicate_mask].copy()
    duplicate_keys_conflict: list[str] = []
    if not duplicate_rows.empty:
        for (d, t), grp in duplicate_rows.groupby(["date", "ticker"], dropna=False):
            compare = grp[PRICE_COLUMNS].astype(object).where(pd.notna(grp[PRICE_COLUMNS]), None)
            if len(compare.drop_duplicates()) > 1:
                duplicate_keys_conflict.append(f"{d} {t}")
        write_csv(duplicate_rows, out_dir / "duplicate_rows.csv")
        if duplicate_keys_conflict:
            raise RuntimeError(
                "Conflicting duplicate date/ticker rows found. Inspect duplicate_rows.csv. Keys: "
                + ", ".join(duplicate_keys_conflict[:20])
            )
        prices = prices.drop_duplicates(subset=["date", "ticker"], keep="first").reset_index(drop=True)
    else:
        write_csv(pd.DataFrame(columns=PRICE_COLUMNS), out_dir / "duplicate_rows.csv")

    # Check OHLC integrity; source values are not silently corrected.
    complete_ohlc = prices[["open", "high", "low", "close"]].notna().all(axis=1)
    bad_ohlc = pd.Series(False, index=prices.index)
    if complete_ohlc.any():
        p = prices.loc[complete_ohlc]
        tol = 1e-8
        bad = (p["high"] + tol < p[["open", "close"]].max(axis=1)) | \
              (p["low"] - tol > p[["open", "close"]].min(axis=1)) | \
              (p["high"] + tol < p["low"])
        bad_ohlc.loc[p.index] = bad
    invalid_ohlc_rows = prices.loc[bad_ohlc].copy()
    write_csv(invalid_ohlc_rows, out_dir / "invalid_ohlc_rows.csv")

    actions_df = pd.DataFrame(all_actions, columns=[
        "date", "ticker", "action_type", "dividend_amount", "split_numerator", "split_denominator",
        "split_ratio", "currency", "source_event_type"
    ])
    if not actions_df.empty:
        actions_df = actions_df.sort_values(["date", "ticker", "action_type"], kind="stable")
    write_csv(actions_df, out_dir / "corporate_actions.csv")
    write_csv(prices, out_dir / "historical_prices.csv")

    # Use NIFTY 50 dates as the primary observed-market-session proxy when available.
    nifty_dates = set(prices.loc[prices["ticker"] == "^NSEI", "date"].dropna().astype(str))
    all_dates = set(prices["date"].dropna().astype(str))
    if nifty_dates:
        reference_dates = sorted(nifty_dates)
        calendar_basis = "dates with a downloaded ^NSEI bar; a proxy, not an official exchange calendar"
    else:
        reference_dates = sorted(all_dates)
        calendar_basis = "union of dates observed for successfully fetched assets; non-authoritative fallback because ^NSEI failed"

    missing_records: list[dict[str, str]] = []
    reference_set = set(reference_dates)
    actual_by_ticker = {t: set(prices.loc[prices["ticker"] == t, "date"].astype(str)) for t in ASSETS}
    for ticker in ASSETS:
        if ticker in fetch_errors:
            missing_records.append({
                "date": "", "ticker": ticker, "reason": "asset_fetch_failed",
                "detail": fetch_errors[ticker], "calendar_basis": calendar_basis,
            })
            continue
        actual = actual_by_ticker.get(ticker, set())
        # Report bars missing on observed reference sessions, never insert/fill them.
        for d in sorted(reference_set - actual):
            missing_records.append({
                "date": d, "ticker": ticker, "reason": "no_observation_on_reference_session",
                "detail": "No source bar for this ticker on a date with a reference-session observation; may be no trade or source gap.",
                "calendar_basis": calendar_basis,
            })
        # If other requested assets have an observation on a date without a NIFTY bar,
        # explicitly flag the reference-index gap instead of overlooking it.
        if ticker == "^NSEI" and nifty_dates:
            for d in sorted(all_dates - actual):
                missing_records.append({
                    "date": d, "ticker": ticker, "reason": "no_NIFTY50_bar_on_other_asset_session",
                    "detail": "At least one other requested asset has a source bar on this date, but ^NSEI has none; verify against the official NSE calendar/source.",
                    "calendar_basis": "union of dates observed for other requested assets; non-authoritative check",
                })
    write_csv(pd.DataFrame(missing_records, columns=["date", "ticker", "reason", "detail", "calendar_basis"]), out_dir / "missing_observations.csv")

    # Construct a common date index without forward-fill or interpolation.
    calendar_dates = sorted(all_dates)
    price_basis_rows: list[dict[str, str]] = []
    series_by_ticker: dict[str, pd.Series] = {}
    indexed = prices.copy()
    indexed["date"] = pd.to_datetime(indexed["date"])
    for ticker in ASSETS:
        asset_rows = indexed[indexed["ticker"] == ticker].sort_values("date")
        if asset_rows.empty:
            basis = "unavailable"
            selected = pd.Series(dtype=float)
            reason = "No downloaded bars; do not infer returns for this asset."
        elif asset_rows["adjusted_close"].notna().any():
            basis = "adjusted_close"
            selected = asset_rows.set_index("date")["adjusted_close"].astype(float)
            reason = "Use Yahoo Finance adjusted close for return calculations; any missing observations remain missing."
        elif asset_rows["close"].notna().any():
            basis = "close"
            selected = asset_rows.set_index("date")["close"].astype(float)
            reason = "Adjusted close is unavailable in the source; use close as a price-return proxy only. For ^NSEI this is a price index, not total return."
        else:
            basis = "unavailable"
            selected = pd.Series(dtype=float)
            reason = "Neither adjusted close nor close has usable observations."
        price_basis_rows.append({"ticker": ticker, "return_price_field": basis, "explanation": reason})
        series_by_ticker[ticker] = selected

    dates_index = pd.to_datetime(calendar_dates)
    wide = pd.DataFrame(index=dates_index)
    wide.index.name = "date"
    for ticker in ASSETS:
        s = series_by_ticker[ticker]
        if not s.empty:
            s.index = pd.to_datetime(s.index)
            wide[ticker] = s.reindex(dates_index)
        else:
            wide[ticker] = np.nan
    write_csv(wide.reset_index(), out_dir / "adjusted_close_wide.csv")

    returns = wide.pct_change(fill_method=None)
    write_csv(returns.reset_index(), out_dir / "daily_returns.csv")
    # Correlations are calculated from pairwise-complete daily returns; no missing values are filled.
    correlation = returns.corr(min_periods=60)
    write_csv(correlation.rename_axis("ticker").reset_index(), out_dir / "correlation_matrix.csv")
    write_csv(pd.DataFrame(price_basis_rows), out_dir / "return_price_basis.csv")

    # Per-asset summary and historical risk metrics. Volatility uses 252 trading days.
    quality_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    for ticker, info in ASSETS.items():
        subset = prices[prices["ticker"] == ticker].copy()
        subset_dates = sorted(subset["date"].dropna().astype(str).unique().tolist())
        duplicate_key_count = int(duplicate_rows[duplicate_rows["ticker"] == ticker]["date"].nunique()) if not duplicate_rows.empty else 0
        miss_count = sum(1 for r in missing_records if r["ticker"] == ticker and r["reason"] == "no_observation_on_reference_session")
        row: dict[str, Any] = {
            "ticker": ticker,
            "asset_name": info["asset_name"],
            "asset_type": info["asset_type"],
            "exchange": info["exchange"],
            "currency": info["currency"],
            "fetch_status": "FAILED" if ticker in fetch_errors else "OK",
            "fetch_error": fetch_errors.get(ticker, ""),
            "observations": len(subset),
            "first_observation": subset_dates[0] if subset_dates else "",
            "last_observation": subset_dates[-1] if subset_dates else "",
            "missing_reference_sessions": miss_count,
            "duplicate_date_ticker_keys": duplicate_key_count,
            "invalid_ohlc_rows": int((invalid_ohlc_rows["ticker"] == ticker).sum()) if not invalid_ohlc_rows.empty else 0,
        }
        for col in NUMERIC_COLUMNS:
            row[f"null_{col}_count"] = int(subset[col].isna().sum()) if not subset.empty else 0
        row["corporate_action_events"] = int((actions_df["ticker"] == ticker).sum()) if not actions_df.empty else 0
        quality_rows.append(row)

        if ticker not in wide.columns:
            continue
        ret = returns[ticker].replace([np.inf, -np.inf], np.nan).dropna()
        price = wide[ticker].dropna()
        if len(price) >= 2:
            total_return = float(price.iloc[-1] / price.iloc[0] - 1)
            first = price.index[0].date().isoformat()
            last = price.index[-1].date().isoformat()
            # Drawdown is calculated directly from observed selected prices, without
            # filling missing returns with zero or manufacturing a flat-price interval.
            observed_wealth = price / price.iloc[0]
            drawdown = observed_wealth / observed_wealth.cummax() - 1.0
            max_drawdown = float(drawdown.min())
        else:
            total_return = np.nan
            first = price.index[0].date().isoformat() if len(price) else ""
            last = price.index[-1].date().isoformat() if len(price) else ""
            max_drawdown = np.nan
        metric_rows.append({
            "ticker": ticker,
            "return_price_field": next((r["return_price_field"] for r in price_basis_rows if r["ticker"] == ticker), "unavailable"),
            "first_price_date": first,
            "last_price_date": last,
            "price_observations": int(len(price)),
            "daily_return_observations": int(len(ret)),
            "period_return_pct": total_return * 100 if pd.notna(total_return) else np.nan,
            "annualized_volatility_pct": float(ret.std(ddof=1) * np.sqrt(252) * 100) if len(ret) >= 2 else np.nan,
            "maximum_drawdown_pct": max_drawdown * 100 if pd.notna(max_drawdown) else np.nan,
            "metric_note": "Derived from downloaded observations only; no imputation. NIFTY 50 uses price returns, not total returns." if ticker == "^NSEI" else "Derived from selected return price field; ETF price return may differ from NAV/total return.",
        })
    write_csv(pd.DataFrame(quality_rows), out_dir / "data_quality_summary.csv")
    write_csv(pd.DataFrame(metric_rows), out_dir / "historical_metrics.csv")

    metadata = {
        "dataset_name": "F-06 Investment Portfolio Risk and Scenario Analysis — Daily Historical Market Dataset",
        "created_at_utc": retrieval_time,
        "requested_start_date_inclusive": start_date.isoformat(),
        "requested_end_date_inclusive": end_date.isoformat(),
        "date_timezone": "Asia/Kolkata (IST, UTC+05:30)",
        "source": SOURCE_NAME,
        "source_homepage": "https://finance.yahoo.com/",
        "source_endpoint_template": SOURCE_BASE + "{URL-encoded ticker}?period1=...&period2=...&interval=1d&events=div,splits",
        "source_references": [
            "https://finance.yahoo.com/quote/TCS.NS/history/",
            "https://finance.yahoo.com/quote/NIFTYBEES.NS/history/",
            "https://in.help.yahoo.com/kb/SLN2311.html",
        ],
        "fetch_status": "PARTIAL" if fetch_errors else "COMPLETE",
        "fetch_errors": fetch_errors,
        "assets": {
            ticker: {
                **asset_info,
                "yahoo_ticker": ticker,
                "source_observations": int((prices["ticker"] == ticker).sum()),
                "source_metadata": per_symbol_info.get(ticker, {}),
            }
            for ticker, asset_info in ASSETS.items()
        },
        "schema": {
            "date": "ISO-8601 market session date in Asia/Kolkata",
            "ticker": "Yahoo Finance symbol; maps are included under assets",
            "open_high_low_close": "Source-provided daily OHLC in INR. Yahoo's Close is generally split-adjusted; see source documentation and verify corporate actions.",
            "adjusted_close": "Yahoo Finance Adj Close where returned; includes dividend/distribution adjustments as well as splits. Blank means source did not provide a value; it is not imputed.",
            "volume": "Source volume where available; blank for assets such as indices without traded volume.",
            "currency": "INR as the denomination for the requested NSE stocks, ETFs and NIFTY 50 index.",
        },
        "return_methodology": {
            "selected_price_field": "adjusted_close when the symbol has adjusted-close observations; otherwise close only when adjusted_close is unavailable for that entire symbol (e.g. the NIFTY 50 price index). See return_price_basis.csv.",
            "daily_returns": "Percentage changes from consecutive observed values. No forward-fill, interpolation or fabricated values. A blank return remains blank when an adjacent observation is absent.",
            "annualized_volatility": "Sample standard deviation of daily returns multiplied by sqrt(252).",
            "maximum_drawdown": "Computed from a wealth index compounded from available daily returns; not a forward-looking risk forecast.",
        },
        "quality_checks": {
            "duplicate_key": "Checked date+ticker duplicates. Exact duplicate rows are removed after being logged in duplicate_rows.csv. Conflicting duplicate values stop the script.",
            "ohlc": "Checked high >= max(open, close), low <= min(open, close), and high >= low; anomalies are listed in invalid_ohlc_rows.csv and not altered.",
            "missing_dates": "Compared each ticker with the observed ^NSEI date set when available; this is a proxy calendar, not an authoritative NSE holiday/session calendar. See missing_observations.csv.",
            "nulls": "Field-specific null counts per asset are in data_quality_summary.csv; nulls remain blank in CSV files.",
            "corporate_actions": "Dividends/distributions and splits returned in Yahoo chart events are listed in corporate_actions.csv. This may not be a complete or authoritative corporate-action ledger.",
        },
        "limitations": [
            "Yahoo Finance chart data is an unofficial endpoint, may be delayed, revised, throttled, unavailable for an instrument, or subject to licensing/redistribution restrictions.",
            "This script records the actual retrieval timestamp when run; the workspace that prepared this script could not directly retrieve the raw market API, so no historical prices are embedded or fabricated in this package.",
            "NIFTY 50 is a price index. Its close-based return excludes index dividend reinvestment; do not compare it as though it were a total-return index.",
            "ETF market prices are not the same as NAV returns; adjusted close should be used for historical price-return calculations, and tracking error/NAV history are outside this dataset.",
            "The shared observed-session comparison can identify asset-specific gaps on dates where the reference index has data; it cannot prove that all sources have no common missing session. An official NSE calendar would be needed for that.",
            "Use the observations for a hackathon/research prototype only; independently verify critical results against licensed or official data before any investment decision.",
        ],
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    write_readme(out_dir / "README.md", metadata, price_basis_rows, quality_rows, metric_rows)

    print("\nOutput files written to:", out_dir)
    print("  historical_prices.csv")
    print("  corporate_actions.csv")
    print("  data_quality_summary.csv")
    print("  missing_observations.csv")
    print("  duplicate_rows.csv")
    print("  invalid_ohlc_rows.csv")
    print("  adjusted_close_wide.csv")
    print("  daily_returns.csv")
    print("  correlation_matrix.csv")
    print("  return_price_basis.csv")
    print("  historical_metrics.csv")
    print("  metadata.json")
    print("  README.md")
    if fetch_errors:
        print("\nWARNING: PARTIAL DATASET. Failed symbols are recorded in metadata.json and the quality report:", file=sys.stderr)
        for ticker, err in fetch_errors.items():
            print(f"  {ticker}: {err}", file=sys.stderr)
        return 1
    print("\nAll requested assets returned data. Check data_quality_summary.csv before analysis.")
    return 0


def write_readme(path: Path, metadata: dict[str, Any], price_basis_rows: list[dict[str, str]],
                 quality_rows: list[dict[str, Any]], metric_rows: list[dict[str, Any]]) -> None:
    asset_lines = []
    for ticker, a in metadata["assets"].items():
        asset_lines.append(f"| `{ticker}` | {a['asset_name']} | {a['asset_type']} | {a['currency']} | {a['source_observations']} |")
    basis_lines = [f"| `{r['ticker']}` | `{r['return_price_field']}` | {r['explanation']} |" for r in price_basis_rows]
    status = metadata['fetch_status']
    content = f"""# F-06 Historical Market Dataset

**Build status:** `{status}`  
**Retrieved at (UTC):** `{metadata['created_at_utc']}`  
**Requested range (inclusive):** `{metadata['requested_start_date_inclusive']}` to `{metadata['requested_end_date_inclusive']}`  
**Session timezone:** `{metadata['date_timezone']}`  
**Source:** {metadata['source']}  
**Dataset currency:** INR for the requested NSE-listed securities/index.

## Files

- `historical_prices.csv`: long-form daily observations; no invented or filled price rows.
- `corporate_actions.csv`: dividends/distributions and splits exposed by the source chart response.
- `data_quality_summary.csv`: coverage, null-field counts, missing reference sessions, invalid OHLC counts and action counts by asset.
- `missing_observations.csv`: per-ticker gaps versus the observed reference-session calendar, or explicit fetch failures.
- `duplicate_rows.csv`: rows participating in duplicate `date` + `ticker` keys. Exact duplicates are logged and collapsed; conflicting duplicates stop the build.
- `invalid_ohlc_rows.csv`: OHLC inconsistencies; rows are reported, not altered.
- `adjusted_close_wide.csv`: wide matrix of selected return-price fields with blank cells preserved.
- `daily_returns.csv`: daily percent changes; no forward-fill or interpolation.
- `correlation_matrix.csv`: pairwise-complete Pearson correlations of daily returns (minimum 60 overlapping returns); no imputation.
- `return_price_basis.csv`: field chosen for each ticker and why.
- `historical_metrics.csv`: period return, annualized volatility and maximum drawdown derived from the downloaded observations.
- `metadata.json`: retrieval timestamp, identifiers, source details, method and limitations.

## Asset identifiers

| Yahoo ticker | Asset | Type | Currency | Downloaded rows |
|---|---|---|---|---:|
{chr(10).join(asset_lines)}

## Return price field selection

| Ticker | Field | Explanation |
|---|---|---|
{chr(10).join(basis_lines)}

Use `adjusted_close` for return/correlation calculations when available: it is the adjusted historical price field returned by Yahoo. Where the data provider does not return adjusted close for the entire instrument, the script uses `close` for that ticker only and explicitly documents it in `return_price_basis.csv`. For `^NSEI`, close-based changes are **price-index returns, not total returns**. It does not synthesize adjusted close for the index.

## Quality and missing-data policy

- Dates are ISO `YYYY-MM-DD` and refer to the India market session.
- Rows only exist when the source supplied an observation. No price is forward-filled, interpolated, or generated.
- Missing sessions are compared with observed `^NSEI` dates when available. The index is a **proxy calendar**, not a definitive NSE exchange calendar; holidays and any market-wide omissions cannot be fully confirmed by this test.
- `volume` can be blank for the index or whenever the source has no volume field/value. Empty fields are intentionally preserved as blanks, not filled with zero.
- Empty `adjusted_close` values mean the source did not supply the field/value. They are not replaced with `close` in `historical_prices.csv`.
- Corporate actions are shown only where returned by the source endpoint; verify significant splits/dividends against official company/exchange records.
- OHLC anomalies and duplicates are exported to dedicated diagnostics, not silently corrected.

## Source and limitations

The script calls the Yahoo Finance chart endpoint at `{metadata['source_endpoint_template']}`. Yahoo's web history pages label `Close` as adjusted for splits and `Adj Close` as adjusted for splits and dividend and/or capital-gain distributions. The chart endpoint is unofficial and its availability, historical fields, and redistribution rights may change. Check the provider's current terms and licensing before redistributing data.

References:
- Yahoo Finance historical prices: https://finance.yahoo.com/quote/TCS.NS/history/
- Yahoo Finance historical data help: https://in.help.yahoo.com/kb/SLN2311.html
- Official NSE Indices historical-data page: https://www.niftyindices.com/reports/historical-data
- NSE FAQ on NIFTY history: https://www.nseindia.com/static/products-services/indices-faqs

## Rebuild

```bash
python -m pip install -r requirements.txt
python build_historical_dataset.py --out f06_historical_dataset
```

To specify an exact range:

```bash
python build_historical_dataset.py --start 2023-10-24 --end 2026-10-24 --out f06_historical_dataset
```

This build records the retrieval time on the machine that downloads the data. The script bundle itself contains no fabricated historical prices. It is intended for hackathon/research prototyping, not as an investment recommendation or a substitute for licensed market data.
"""
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
