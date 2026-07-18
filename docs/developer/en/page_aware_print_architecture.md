# Page-aware print, boundary, and visual-regression architecture

Revision: 5 · GAS RATIO PRO v225.7

## Page-aware pipeline

`VisualizationScenePipeline` → `VisualizationPageAwarePackageBuilder` → `VisualizationCrossFormatParityGate` remains the single geometry source for SVG/PNG/PDF/DOCX/HTML. `export_ready` requires a valid package and a passing parity gate.

## Repaired architecture boundaries

- destructive filesystem operations are owned by `TemporaryFileApplicationService`/`DeleteEngine`, not Streamlit UI;
- `ApplicationServiceContainer` owns one session-scoped `CacheMetricsRegistry`;
- correlation artifacts are created through the application service;
- route lifecycle, startup diagnostics, and project cache coherence belong to `RuntimeDiagnosticsApplicationService`;
- direct `st.rerun()` is allowed only inside the unified refresh gate;
- UI creates no infrastructure objects and sends no raw DataFrame downstream.

## Print readability

`reports.print_readability_contract.REPORT_PRINT_READABILITY` is the shared PDF/DOCX contract. It fixes minimum legend fonts, raster dimensions, and the `one-item-per-row` layout. Tests validate the public contract and renderer behaviour instead of source text.

## Controlled visual rebaseline

`config/visual_rebaseline_contracts_v225_7.json` contains 13 approved semantic contracts and a SHA-256 for every canonical JSON snapshot. `VisualRebaselineRegistryService` rejects unregistered or unapproved changes. Original nodeids are preserved.

## Legacy remediation

`config/legacy_regression_contracts_v225_7.json` tracks all 51 inherited contracts. In v225.7 all 51 have `status=resolved`, `resolved_in=v225.7`, and evidence. Silent `xfail`, nodeid deletion, and unreviewed hash updates are forbidden.

## Build identity

`BUILD_VERSION` is the single version source for Python runtime and the PowerShell launcher. `core.build_info` reads it at import time; `DEPLOYMENT_BUILD.txt` must contain the same version.
