# Page Chrome & Print Center Contract v225.3

## Goal

Add shared physical headers, footers, page numbering, and a repeated legend, and expose the exact profile and page count to Print Center from one page-aware package.

## Implemented

1. `VisualizationPrintLayout` v2.1 reserves header/footer/legend regions.
2. `chrome_primitives` are built once in `page_pt` coordinates.
3. SVG and PDF draw the same primitives; PNG is produced from SVG.
4. Geometry signature v3 includes page chrome.
5. `VisualizationPageAwarePackage` v1.1 exposes the chrome contract and counts.
6. `VisualizationPrintCenterService` provides a localized ru/kk/en summary.
7. LAS Viewer export uses one package for SVG/PDF/PNG.
8. QA checks the combined render-model and page-chrome primitive set.

## Acceptance criteria

- every physical page contains a page number;
- the legend repeats without layout recalculation;
- PDF/SVG/PNG have the same page count and signature;
- A4/A3 readability floors remain intact;
- the single-page fallback is disabled;
- ru/kk/en documentation is synchronized.
