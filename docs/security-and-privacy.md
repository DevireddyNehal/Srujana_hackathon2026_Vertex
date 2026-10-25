# Security and Privacy

## Authentication and authorization

The F-06 API has no authentication dependency. Any client that can reach the configured origin can submit portfolio data and scenarios. The journal's `get_current_user_id` always returns `demo`, so all journal requests share one demo identity. This is not multi-user authorization and must not protect private trade records.

The statistics service allows demo accounts and rejects non-demo accounts with an authentication-related message, but it does not implement a real user session in the inspected service. TradeFXBook has demo-user and token-shaped behavior, but its source contains demo secret defaults and must not be considered production authentication.

## Input validation and storage

The main F-06 request models reject unknown fields and enforce bounds for profile values, shocks, asset amounts, and ticker uniqueness. Contagion and reverse-stress request models intentionally ignore unknown fields and accept flexible dictionaries/lists, so their payload surface is less strict. Journal models validate timestamps, prices, sides, quantities, fees, stop-loss relationships, tags, and trade timing.

F-06 analysis results are held in a process-local Python dictionary and can contain portfolio and scenario data. Journal records are written to SQLite. There is no documented encryption-at-rest, retention policy, deletion endpoint for analysis records, backup policy, or multi-process storage design.

## Network and CORS

CORS defaults to `http://localhost:5173`, `http://127.0.0.1:5173`, and `http://localhost:3000`, and can be overridden with `CORS_ORIGINS`. Credentials are disabled, methods are limited to GET/POST/OPTIONS, and all headers are allowed. CORS controls browser access; it is not authentication or authorization.

## Secrets and logging

The F-06 app reads `LOG_LEVEL` and logs exceptions. Error responses intentionally expose high-level diagnostics, while server logs may contain stack traces. No secret is required by the F-06 engine. TradeFXBook defines hard-coded demo `SECRET_KEY` and password-salt defaults in source; these must be replaced and required at deployment time.

Do not commit `.env` files, API keys, private keys, real portfolio records, or production database files. The historical dataset has external attribution and redistribution considerations; it should be reviewed before publication.

## Financial and privacy posture

The system handles portfolio and trade-like data but does not implement privacy controls beyond the demo identity and local storage boundaries. Risk outputs are deterministic or statistical model outputs with assumptions and can be wrong. They are not guaranteed predictions, financial advice, tax advice, or legal advice.

## Recommended remediation

1. Add a verified identity provider and enforce per-user authorization.
2. Remove insecure default secrets and use deployment secret management.
3. Define retention, deletion, encryption, backup, and audit-log policies.
4. Tighten flexible request models and add negative security tests.
5. Restrict CORS to known deployment origins and review error/log disclosure.
6. Review market-data licensing and scrub sensitive demo artifacts before release.
