# Data Sources

## F-06 demo portfolios

`mock-data/portfolios.json` contains three static demo portfolios: tech-heavy, conservative-retiree, and all-weather-balanced. Each stores an investor profile and holdings with INR amounts, sectors, asset classes, liquidity tags, and currency exposure. The API validates this file at request time. These holdings are fixtures, not live positions or live quotes.

The frontend also contains a local copy and display assumptions in `frontend/src/pages/website/portfolioData.ts`. Those values include illustrative returns, volatility, and FX exposure used by the website display. The frontend copy should not be described as a live market-data feed.

## Historical dataset artifacts

`f06_historical_dataset/README.md` records a retrieval from the unofficial Yahoo Finance chart endpoint for:

- TCS.NS
- INFY.NS
- HDFCBANK.NS
- ^NSEI
- GOLDBEES.NS
- LIQUIDBEES.NS

The documented requested range is 2023-10-24 through 2026-10-24, with 740 rows per listed identifier in the recorded build. Artifacts include prices, adjusted-close wide data, daily returns, corporate actions, correlations, quality summaries, missing observations, duplicate diagnostics, invalid OHLC diagnostics, return-price basis, metrics, and metadata.

The dataset preserves missing observations, does not forward-fill or interpolate, treats the index as a price index rather than total return, and warns that the Yahoo endpoint is unofficial. Corporate actions should be checked against official sources. Redistribution and licensing have not been verified by this audit.

## Runtime linkage

The repository contains historical CSV data, but the inspected `compute_stochastic_cone_and_history` implementation generates the API's twelve historical observations from fixed multipliers and month labels. The F-06 API does not demonstrate a runtime read of the CSV artifacts in that function. This is a material distinction: repository data availability is not evidence that the displayed chart is calculated from the downloaded files.

## External services

The dataset build script calls Yahoo Finance's chart URL documented in the dataset README. The inspected F-06 API does not call Yahoo Finance at request time. No external LLM, quote service, or portfolio provider is configured in the F-06 manifests or engine code.

## Synthetic and generated data

The trading-statistics service seeds synthetic closed trades into SQLite by default. TradeFXBook also generates deterministic demo trades. These datasets are for demonstration and testing; they are not market observations or investment evidence.
