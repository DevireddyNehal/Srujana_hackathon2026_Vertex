# Testing

## Test inventory

- `tests/test_analytics.py`, `test_engine.py`, `test_metrics.py`, `test_router.py`, `test_storage.py`, and `test_tradefxbook.py` are repository-level pytest tests.
- `backend/trading_user_stats/tests/` contains API, large-dataset, and statistics tests.
- The frontend declares `npm run lint` and `npm run build`; no frontend unit or browser end-to-end runner is declared.
- Historical dataset quality is represented by exported diagnostic files and the build script, not by an application coverage report.

## Executed checks on 2026-10-25

| Command | Result | Evidence |
| :--- | :--- | :--- |
| `python -m pytest -q` | Blocked during collection | `tests/test_tradefxbook.py` imports missing `pydantic_settings` |
| `frontend: npm run lint` | Passed | `oxlint` exited 0 |
| `frontend: npm run build` | Passed | TypeScript and Vite production build exited 0 |
| F-06 `GET /health` via `TestClient` | Passed | HTTP 200 and `{"status":"ok"}` |
| F-06 `GET /api/portfolios` via `TestClient` | Passed | HTTP 200 and 3 portfolios |
| F-06 `GET /openapi.json` via `TestClient` | Passed | HTTP 200 and 11 paths |
| F-06 `POST /api/analyze-scenario` via `TestClient` | Passed | HTTP 200 using first fixture portfolio |
| F-06 `POST /api/contagion/simulate` via `TestClient` | Passed | HTTP 200 using first fixture portfolio |
| F-06 `POST /api/reverse-stress-test` via `TestClient` | Passed | HTTP 200 using first fixture portfolio |

These smoke calls exercised the application in-process, not a separately spawned Uvicorn process or a browser.

## Dependency finding

`tradefxbook/config.py` imports `pydantic-settings`. The root `requirement.txt` declares `pydantic-settings`, but `backend/requirements.txt` does not. The current active environment lacks the package, which blocks collection of the TradeFXBook test module. The statistics development requirements do not resolve this TradeFXBook dependency because they are scoped to the statistics service.

The fix should be a dependency-management decision by the team: either install the correct service-specific requirements when testing TradeFXBook or add a clearly scoped TradeFXBook requirements manifest. This documentation task did not modify requirements files.

## Untested or partially tested areas

- No browser workflow was executed.
- No separately spawned frontend/backend process was exercised.
- Invalid-input responses for every route were not exhaustively tested.
- Journal CRUD and identity isolation were not included in the smoke probe.
- Statistics startup seeding and its full test suite were not rerun in this audit.
- No coverage percentage or performance benchmark is claimed.
