# Audit Summary

## Applications found

1. F-06 portfolio risk API and React/Vite frontend.
2. Trading journal routes mounted in the F-06 FastAPI app.
3. Separate trading-user-statistics FastAPI service with synthetic SQLite data.
4. Separate TradeFXBook API, CLI, and static dashboard.

## Main entry points

- `backend.main:app`
- `trading_user_stats.app.api:app` with `--app-dir backend`
- `run_tradefxbook.py` or `python -m tradefxbook.cli`
- `frontend/package.json` Vite scripts

## Corrected documentation findings

- Backend source exists; the prior claim that it was absent was incorrect.
- The F-06 API includes health, portfolio, scenario, contagion, reverse-stress, and Butterfly routes, plus mounted journal routes.
- The earlier directory summary omitted `contagion.py` and other services.
- The frontend setup contained a PowerShell `Copy-Item` command inside an unspecified shell block; the new setup guide labels PowerShell and Bash separately.
- The statistics service has separate runtime and development manifests; the documentation now identifies the development manifest as the test/install entry point.
- `backend/requirements.txt` omits `httpx` and `pydantic-settings`; TradeFXBook imports the latter, which explains current test collection failure.
- The F-06 chart function uses fixed display history and does not demonstrate runtime CSV loading.
- The F-06 “AI” path is deterministic rule and heuristic code; no external LLM was verified.

## Verification boundary

In-process FastAPI smoke tests passed for health, portfolios, OpenAPI, scenario analysis, contagion, and reverse stress. Frontend lint and build passed. The full Python suite did not collect because of the missing dependency. A browser workflow, separately spawned services, journal CRUD, statistics startup, deployment, licensing, and team disclosures remain unverified.
