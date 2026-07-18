# Page-aware print and direct-preview architecture

Revision: 3 · GAS RATIO PRO v225.5

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
