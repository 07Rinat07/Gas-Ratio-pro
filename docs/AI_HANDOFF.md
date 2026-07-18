# Latest implementation — Stable Promotion & Live Workbench Acceptance v225.8

## Release state

- Build: `v225.8`.
- Channel: `stable`.
- Stage 4 Workbench UI Completion is complete.
- Live acceptance result: **14/14 passed**.

## Acceptance architecture

- `services/workbench_live_acceptance.py` starts and cleans up a temporary Streamlit server, polls `/_stcore/health`, and executes UI contracts through official AppTest.
- `scripts/run_live_workbench_acceptance.py` is the cross-platform CLI.
- `run_app.ps1 -Acceptance` is the Windows entry point.
- `config/live_workbench_acceptance_contract_v225_8.json` is the mandatory promotion policy.
- Evidence is stored in `artifacts/acceptance/live_workbench_acceptance_v225_8.json`.

## Verified behavior

- absolute source/build identity;
- Toolbar, Project Explorer, Workspace Host, Properties, and Status Bar;
- command-backed LAS navigation;
- LAS Viewer and LAS Workspace open action without traceback;
- temporary server termination after acceptance.

## Verification

- Live acceptance: **14/14 passed**.
- Full regression suite: **2858 passed, 0 failed**.
- Architecture debt: 0; active legacy contracts: 0.

## Next authorized stage

Stage 5 — Petrophysical Engine Validation Foundation: Method Registry freeze, formula/source provenance, reference datasets, numerical tolerances, uncertainty metadata, and one application-service validation gate. Interpretation 2.0 and approved visual baselines remain frozen.

## Release governance

Always update and verify Russian, Kazakh, and English README, user instructions, developer architecture, status, roadmap, project plan, changelog, release notes, and documentation manifest. User archives exclude `.github/workflows` unless local runtime explicitly requires it.
