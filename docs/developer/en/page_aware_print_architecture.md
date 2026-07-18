# Page-aware print and direct-preview architecture

Revision: 2 · GAS RATIO PRO v225.4

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
