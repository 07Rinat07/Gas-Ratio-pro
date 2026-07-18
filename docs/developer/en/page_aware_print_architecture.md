# Page-aware print and direct-preview architecture

Revision: 4 · GAS RATIO PRO v225.6

## Single geometry source

`VisualizationScenePipeline` creates physical `VisualizationPrintLayout` v2.1. `VisualizationPageAwarePackageBuilder` produces package v1.2 with every SVG/PNG page, one multi-page PDF, geometry signature v3, page chrome, and QA results.

## Application bridge

`ReportPageAwarePreviewService` is the only boundary from the current report `DataFrame` to the physical package. It calls `LasVisualizationPayloadService.build_from_frame()`, then `VisualizationPrintCenterService.prepare()`, and attaches a renderer-neutral payload to `PresentationModel`.

Raw `DataFrame` rows are not passed downstream.

## Preview contract v1.1

The canonical `visualization.preview.page-aware` contract contains a `pages` array. Each page carries `index`, `track_ids`, `width_pt`, `height_pt`, chrome primitive count, and the completed SVG. `single_page_fallback=false` and `legacy_svg_fallback_allowed=false` are mandatory.

`reports.visualization_preview.normalize_visualization_preview()` is the shared strict normalizer for HTML, DOCX, PDF, and asset export. For a page-aware schema it never uses compatibility `svg` or `page_svgs` fields when canonical `pages` are absent.

## Visible Print Center

`build_professional_print_center_view()` projects one prepared package into a UI contract containing the exact profile, status, geometry signature, and every preview page. Streamlit caches the result by the parameter signature and passes the same report payload into export.

## Invariants

- one pipeline and one geometry signature;
- downstream layout is never rebuilt;
- DOCX/HTML receive all physical pages directly;
- the `bundle` format uses the same package;
- labels and messages remain synchronized for `ru/kk/en`;
- page-count mismatch invalidates preview readiness;
- legacy static-export branches may be removed only after parity audit.

## Cross-format parity gate v1.0

`VisualizationCrossFormatParityGate` runs inside `VisualizationPageAwarePackageBuilder`. It compares layout pages, package pages, SVG root dimensions, PNG IHDR dimensions, actual PDF page count, canonical preview pages, track partition, and geometry signature. `VisualizationPageAwarePackage.export_ready` requires `parity_gate.ok=true`.

`VisualizationPageAwarePackage` is upgraded to v1.3. `VisualizationPrintCenterSummary` and the UI view model publish `parity_gate_id` and `cross_format_parity_passed`.

## User physical profiles

`UserPhysicalPrintProfileStore` persists JSON schema `gas-ratio-pro.physical-print-profiles` in `data/user_preferences/physical_print_profiles.json`. `VisualizationPrintLayoutEngine` accepts a serialized `physical_profile`. User A4/A3 profiles may strengthen readability floors and reduce page capacity, but cannot weaken the baseline constraints.

## Static-export retirement

Professional reports and LAS Viewer use `build_page_aware_static_artifact()`. Single-page SVG/PNG is delivered directly; multi-page output is a manifest-backed ZIP. The independent CompositeLog SVG/PNG/PDF branch in `reports.export_static` is removed and replaced with an explicit legacy-path prohibition. Ordinary Plotly charts remain on Kaleido and are not treated as physical Print Center documents.

## Physical golden artifacts v225.6

`VisualizationPhysicalGoldenArtifactService` renders one ten-track renderer-neutral fixture through `a4_portrait`, `a4_landscape`, `a3_portrait`, and `a3_landscape`. Every physical page is stored as SVG and PNG, and each profile has one multi-page PDF. `manifest.json` records SHA-256, point/pixel dimensions, track partition, chrome primitive count, geometry signature, and parity gate id.

The baseline may be updated only with `python scripts/regenerate_physical_golden_artifacts.py` after visual review. The regeneration test compares structural signatures and visual checksums.

## End-to-end Print Center acceptance

`ProfessionalPrintCenterAcceptanceRunner` executes the application-level path without passing raw DataFrames downstream: profile store → `ReportPageAwarePreviewService` → visible view model → `PresentationModel` → HTML/PDF/DOCX bundle → SVG/PNG static delivery. Evidence is written as `print-center-acceptance-report.json`.

PDF embedding now uses `_AutoScaleRasterImage`. The physical preview size is calculated in `wrap()` from the actual `avail_width` and `avail_height`, preventing ReportLab `LayoutError` for portrait/landscape combinations.

## Legacy regression audit

`config/legacy_regression_contracts_v225_6.json` contains all 51 inherited failures. Every contract has a category, disposition, severity, rationale, and replacement contract. Policy forbids silent `xfail`, hidden architecture debt, and deleting tests without replacements.
