# Submission Checklist

Statuses use only: Verified complete, Partially complete, Not complete, Not verified, or Not applicable.

| Requirement | Status | Evidence and remaining action |
| :--- | :--- | :--- |
| Official F-06 problem statement | Verified complete | `PROBLEM_STATEMENT.md` is present; confirm event wording and version |
| Source repository | Verified complete | Application source, tests, manifests, fixtures, and dataset artifacts are present |
| Focused README | Partially complete | Root README is updated; final team and license details remain |
| Detailed documentation | Verified complete | `docs/` contains architecture, setup, API, engine, data, testing, security, limitations, AI, and checklist documents |
| Reproducible backend setup | Partially complete | Command and entry point are verified; dependency manifests are inconsistent |
| Reproducible frontend setup | Verified complete | `npm run lint` and `npm run build` passed from `frontend/` |
| Working F-06 backend health | Verified complete | `GET /health` returned 200 in an in-process smoke test |
| Portfolio loading | Verified complete | `GET /api/portfolios` returned 200 and 3 portfolios |
| Scenario analysis | Verified complete | First fixture portfolio returned HTTP 200 in smoke test |
| Contagion simulation | Verified complete | First fixture portfolio returned HTTP 200 in smoke test |
| Reverse stress test | Verified complete | First fixture portfolio returned HTTP 200 in smoke test |
| Browser-to-backend demo | Not verified | Run separately started services and a browser workflow |
| Python test suite | Partially complete | Collection blocked by missing `pydantic-settings`; rerun after dependency resolution |
| Supporting data attribution | Partially complete | Dataset metadata is present; redistribution/licensing requires confirmation |
| AI-use disclosure | Not complete | Confirm development tools and human review |
| Team contribution record | Not complete | Confirm contributors, responsibilities, and review evidence |
| Demo video | Not verified | Provide the final recording and verify it reflects current behavior |
| Deployment configuration | Not applicable | No deployment target was established in the repository |
| License | Not complete | Select and add a license or state an explicit restriction |

Documentation does not replace a working demonstration, complete source submission, dependency installation, or event-specific submission requirements.
