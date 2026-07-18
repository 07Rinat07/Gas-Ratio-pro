# Latest implementation — Architecture and contract remediation v225.7

## Architecture boundaries

- `TemporaryFileApplicationService` owns validated destruction through `DeleteEngine`.
- `ApplicationServiceContainer.cache_metrics_registry()` provides one session-scoped telemetry registry.
- Runtime diagnostics application service owns route lifecycle, startup diagnostics, and cache coherence.
- Correlation artifacts are passed through application-service APIs.
- Direct Streamlit rerun is permitted only inside the unified rerun gate.

## Behavioral contracts

- `core/ui_behavior_contracts.py` defines executable documentation, export, navigation, launcher, and search behavior.
- Tests no longer inspect source text to prove UI behavior.
- Workbench renderer helpers expose current build badge and navigation behavior.
- Root `BUILD_VERSION` is the single runtime build source; `run_app.ps1` reads it dynamically.

## Controlled visual rebaseline

- `services/visual_rebaseline_registry.py` builds canonical semantic snapshots and validates SHA-256.
- Approved contracts live in `config/visual_rebaseline_contracts_v225_7.json`.
- `tests/visual_rebaseline_helpers.py` extracts renderer behavior without relying on incidental trace counts.
- All 13 former visual legacy assertions now use approved semantic contracts.

## Legacy regression registry

- `config/legacy_regression_contracts_v225_7.json` contains all 51 inherited contracts.
- Every entry is resolved in v225.7 and includes evidence plus a replacement contract.
- Active legacy debt is zero.
- Silent `xfail` and deletion without replacement remain prohibited.

## Verification

- Extended architecture/renderer/export/documentation set: **480 passed**.
- Complete regression suite: **2855 passed, 0 failed**.
- All 51 legacy nodeids pass their replacement contracts.
- Stable promotion remains blocked only by live Workbench acceptance.

## Release governance

- Build: `v225.7`, channel `release-candidate` until live Workbench acceptance completes.
- User release archives exclude `.github/workflows` unless local runtime explicitly requires it.
- Always update and verify Russian, Kazakh, and English README, user instructions, developer architecture, status, roadmap, project plan, changelog, release notes, and documentation manifest.
