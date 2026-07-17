# Current status — v225.3

Updated: 18 July 2026.

The **Page Chrome & Print Center Contract** increment is complete:

- `VisualizationPrintLayout` was upgraded to version 2.1;
- each physical page now contains separate `header_bounds`, `footer_bounds`, `legend_bounds`, and `chrome_primitives`;
- title, subtitle, classification, document code, footer, page number, and repeated legend are built once in `page_pt` coordinates;
- Russian, Kazakh, and English page-number and legend labels are synchronized;
- SVG and PDF draw the same page-space primitives, while PNG is rasterized from those SVG pages;
- geometry signature v3 includes physical page regions and page chrome;
- `VisualizationPageAwarePackage` was upgraded to version 1.1;
- `VisualizationPrintCenterService` now exposes the exact profile, orientation, DPI, and page count;
- LAS Viewer export now uses one page-aware package for SVG/PDF/PNG;
- the single-page fallback remains disabled.
- background export is dispatched through `ThreadPoolExecutor`, so progress and cooperative cancellation work while the job is running;

User and developer documentation was updated consistently in `ru / kk / en`, and the documentation manifest was extended.

Next approved increment: connect the localized physical-package summary to the visible Professional Print Center, pass page-aware preview directly to DOCX/HTML, and remove remaining independent legacy static-export branches after parity verification.

## Release governance

Current stage: **Stabilization & Release Audit**. **Release candidate v225.3** is being verified against the unified page-aware pipeline, synchronized three-language documentation, and reproducible reference artifacts.

## v225.3 verification

- 362 focused renderer, Print Center, background-export, and documentation-governance tests pass;
- Python compileall and relative-link validation pass;
- the complete 2831-test suite did not finish within the available execution window; the first diagnostic batch of 20 failures was compared with the original v225.2 archive;
- 2 roadmap-contract failures were fixed in v225.3, while the remaining 18 failures in that sample reproduce unchanged in v225.2; possible later legacy failures were not classified;
- the build remains a release candidate pending a separate complete audit of obsolete legacy-UI test contracts.
