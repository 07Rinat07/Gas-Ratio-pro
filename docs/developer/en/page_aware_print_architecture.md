# Page-aware print architecture

Revision: 1 · GAS RATIO PRO v225.3

## System boundary

`VisualizationScenePipeline` calculates physical `VisualizationPrintLayout` version 2.1. Each page contains `content_bounds`, `header_bounds`, `footer_bounds`, `legend_bounds`, `track_ids`, and `chrome_primitives`.

`chrome_primitives` use `coordinate_space=page_pt`. SVG and PDF must draw them without another scale transform and without the content clip. PNG is rasterized from the completed SVG pages.

## Unified package

`VisualizationPageAwarePackageBuilder` produces one version 1.1 package containing:

- every SVG page;
- every PNG page;
- one multi-page PDF;
- geometry signature v3;
- the page chrome contract;
- the QA result.

`VisualizationPrintCenterService` creates a localized ru/kk/en summary and one output contract for PDF, SVG, PNG, and DOCX/HTML preview. Downstream layout rebuilding is prohibited.

## Invariants

- one pipeline is the only geometry source;
- page numbers and legends have identical coordinates in every renderer;
- page count and track partition match across formats;
- `single_page_fallback` is `false`;
- a legacy path may be removed only after parity tests pass.
