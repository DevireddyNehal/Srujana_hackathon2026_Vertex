# F-06 Historical Market Dataset

**Build status:** `COMPLETE`  
**Retrieved at (UTC):** `2026-10-24T17:56:39+00:00`  
**Requested range (inclusive):** `2023-10-24` to `2026-10-24`  
**Session timezone:** `Asia/Kolkata (IST, UTC+05:30)`  
**Source:** Yahoo Finance Chart endpoint (unofficial endpoint; see README limitations)  
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
| `TCS.NS` | Tata Consultancy Services Limited | Equity | INR | 740 |
| `INFY.NS` | Infosys Limited | Equity | INR | 740 |
| `HDFCBANK.NS` | HDFC Bank Limited | Equity | INR | 740 |
| `^NSEI` | NIFTY 50 Index | Equity index (price index) | INR | 740 |
| `GOLDBEES.NS` | Nippon India ETF Gold BeES | Gold ETF | INR | 740 |
| `LIQUIDBEES.NS` | Nippon India ETF Liquid BeES | Liquid debt ETF | INR | 740 |

## Return price field selection

| Ticker | Field | Explanation |
|---|---|---|
| `TCS.NS` | `adjusted_close` | Use Yahoo Finance adjusted close for return calculations; any missing observations remain missing. |
| `INFY.NS` | `adjusted_close` | Use Yahoo Finance adjusted close for return calculations; any missing observations remain missing. |
| `HDFCBANK.NS` | `adjusted_close` | Use Yahoo Finance adjusted close for return calculations; any missing observations remain missing. |
| `^NSEI` | `adjusted_close` | Use Yahoo Finance adjusted close for return calculations; any missing observations remain missing. |
| `GOLDBEES.NS` | `adjusted_close` | Use Yahoo Finance adjusted close for return calculations; any missing observations remain missing. |
| `LIQUIDBEES.NS` | `adjusted_close` | Use Yahoo Finance adjusted close for return calculations; any missing observations remain missing. |

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

The script calls the Yahoo Finance chart endpoint at `https://query1.finance.yahoo.com/v8/finance/chart/{URL-encoded ticker}?period1=...&period2=...&interval=1d&events=div,splits`. Yahoo's web history pages label `Close` as adjusted for splits and `Adj Close` as adjusted for splits and dividend and/or capital-gain distributions. The chart endpoint is unofficial and its availability, historical fields, and redistribution rights may change. Check the provider's current terms and licensing before redistributing data.

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
