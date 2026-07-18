# GAS RATIO PRO Changelog
## v225.10 — Field Calibration, Sensitivity & Report Authorization — 2026-07-18

- added a project-owned synthetic field-surrogate dataset for 10 methods;
- added RMSE/MAE/bias, sensitivity, and uncertainty envelopes;
- wired final-report authorization before PresentationModel/renderer execution;
- persisted method context and authorization evidence in artifacts/history;
- added ru/kk/en read-only diagnostics to Professional Print Center;
- foundation Dual Water remains `blocked_final_report`;
- production formulas were not changed.

- Final v225.10 verification: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.

## v225.9 — Petrophysical Engine Validation Foundation — 2026-07-18

- registered 10 petrophysical methods with provenance, units, applicability, limitations, and report policy;
- added 10 synthetic reference cases, numerical tolerances, and uncertainty metadata;
- added an application-service validation gate, CLI, and JSON evidence;
- calculation manifests include method provenance and the contract fingerprint;
- foundation Dual Water is blocked for final reports.
- the A3 landscape renderer now uses the actual page/frame size; plots and narrative tables span the full working frame.
- PDF/DOCX/HTML are synchronized by `print-readability/v1.1` and the controlled visual baseline v225.9.

- result: petrophysical gate 10/10, Live Workbench 14/14, full regression suite **2881 passed, 0 failed**.

## v225.8 — Stable Promotion & Live Workbench Acceptance — 2026-07-18

- promoted the build channel to `stable` after 14/14 live acceptance checks;
- added a real Streamlit server health gate and executable AppTest session;
- verified build/source identity and all five Workbench regions;
- confirmed the LAS command and LAS Workspace without a traceback;
- added a CLI, `run_app.ps1 -Acceptance`, a machine-readable contract, and JSON evidence;
- opened the Petrophysical Engine Validation Foundation stage.

## v225.7 — Architecture Boundaries, Behavioral Contracts & Controlled Rebaseline

- Removed nine architecture-boundary violations without disabling audit checks.
- Moved temporary-file lifecycle to an application service backed by `DeleteEngine`.
- Made cache telemetry a session-scoped application-container dependency.
- Moved route/startup/cache-coherence lifecycle ownership to the application service.
- Routed every Streamlit rerun through one gate.
- Replaced 26 brittle source assertions with runtime/view-model behavior tests (18 legacy, one Print Center contract, and seven PDF preview contracts).
- Migrated 13 visual contracts to approved semantic snapshots with SHA-256 validation.
- Replaced historical version pins with current-build identity contracts.
- Resolved all 51 legacy regression contracts with evidence and replacement contracts.
- Added the root `BUILD_VERSION` file as the single version source.
- Synchronized documentation and instructions in `ru/kk/en`.
- Complete regression suite: **2855 passed, 0 failed**; extended release set: **480 passed**.

## v225.6 — Physical Golden Baseline & Print Center Acceptance

- Added SVG/PNG/PDF golden artifacts for A4/A3 portrait/landscape profiles.
- Added the end-to-end Professional Print Center acceptance runner.
- Fixed the mixed-orientation physical-preview PDF `LayoutError`.
- Registered all 51 legacy regression contracts without silent `xfail`.
