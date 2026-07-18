# GAS RATIO PRO Changelog

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
