# Known Limitations Register

| ID | Finding | Evidence | User impact | Severity | Status | Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| K-001 | Full Python test collection is blocked | `tradefxbook/config.py` imports `pydantic_settings`; current environment lacks it | Complete regression status is unknown | High | Confirmed | Install service-specific dependencies and rerun tests |
| K-002 | Backend requirement manifests are inconsistent | `backend/requirements.txt` omits `httpx` and `pydantic-settings`; root manifest includes them | Clean setup may work for one service but fail for another | High | Confirmed | Define per-service manifests or a documented aggregate install |
| K-003 | F-06 analysis storage is not durable | `backend/database.py` uses a process-local dictionary | Results disappear on restart and are not shared across workers | Medium | Confirmed | Use durable storage with access and retention policy |
| K-004 | F-06 has no real authentication | `backend/journal/identity.py` returns `demo`; main routes have no auth dependency | Reachable clients can submit/read demo-scoped data | High | Confirmed | Add verified identity and authorization |
| K-005 | Chart history is not linked to CSV runtime data | `compute_stochastic_cone_and_history` uses fixed months/multipliers | Users may assume displayed history came from the downloaded dataset | High | Confirmed | Load validated dataset artifacts or label the series as illustrative |
| K-006 | Alternative allocation uses fixed assumptions | `generate_alternative_rebalance` always uses fixed weights and 3.2% opportunity cost | Results may not fit all portfolios or market regimes | Medium | Confirmed | Parameterize assumptions and expose provenance |
| K-007 | Contagion and flexible routes are less strict | Contagion/reverse models ignore unknown fields and accept raw dictionaries | Malformed or unexpected data may reach engine code | Medium | Confirmed | Add strict schemas and negative tests |
| K-008 | Demo secret defaults exist | `tradefxbook/config.py` defines source defaults for secret key and password salt | Unsafe if deployed without overrides | High | Confirmed | Require secrets and fail closed outside demo mode |
| K-009 | Market-data redistribution is unverified | Dataset README identifies an unofficial Yahoo endpoint and licensing caveat | Submission or public redistribution may have compliance risk | High | Confirmed | Verify provider terms and final attribution |
| K-010 | End-to-end browser workflow not verified | No browser test runner is declared; smoke tests used in-process TestClient | UI/API integration could still regress | Medium | Unverified behavior | Run browser and separately spawned service checks |
| K-011 | No operational deployment controls | No Docker, CI, monitoring, backup, or load-test configuration found | Deployment repeatability and recovery are unknown | Medium | Confirmed | Add deployment and operational controls if required |
| K-012 | No repository license established | No license file was found during audit | Reuse and submission rights are ambiguous | Medium | Confirmed | Select and document a license or explicit restriction |

These limitations are not claims that the application is unusable. They define what the current source and executed checks do and do not establish.
