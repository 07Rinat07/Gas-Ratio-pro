# Live Workbench Acceptance architecture

Revision: 1. Contract: `gas-ratio-pro/live-workbench-acceptance/v1`.

## Components

- `services/workbench_live_acceptance.py` — orchestration, health polling, UI contract inspection, and process cleanup;
- `scripts/run_live_workbench_acceptance.py` — cross-platform CLI;
- `config/live_workbench_acceptance_contract_v225_8.json` — required checks and promotion policy;
- `run_app.ps1 -Acceptance` — Windows entry point;
- `tests/test_live_workbench_acceptance_v225_8.py` — integration regression contract.

## Two verification layers

1. A real `python -m streamlit run` subprocess proves that the server starts and returns `ok` from `/_stcore/health`.
2. Official `streamlit.testing.v1.AppTest` creates an executable Streamlit session, inspects the Workbench regions, and exercises LAS command navigation.

An HTTP 200 response alone is insufficient because the Streamlit script may not execute before a session connects. AppTest alone is also insufficient because it does not prove the launcher/server boundary.

## Promotion policy

All 11 check IDs are mandatory. Silent skip is forbidden. Runtime identity must match the absolute `PROJECT_ROOT`, `BUILD_VERSION`, `BUILD_CHANNEL`, and entry point. The temporary subprocess must be stopped in `finally` for every outcome.
