# Print Center and physical pages

Revision: 1 · GAS RATIO PRO v225.3

## What changed

An engineering log panel is now prepared as one physical page package. Before export, the Print Center can show the exact paper profile, orientation, DPI, and page count. PDF, SVG, PNG, and DOCX/HTML preview use the same track partition and geometry signature.

## Page chrome and repeated legend

When `page_chrome` is enabled, every page contains:

- title and subtitle;
- document classification and code;
- footer;
- page numbering in the form “Page N / M”;
- a repeated legend for curves and intervals.

Page chrome is built in physical page coordinates and is not scaled down with engineering tracks.

## Recommended workflow

1. Select A4 or A3 and the orientation.
2. Verify the exact page count in the Print Center summary.
3. Confirm that service page chrome and the legend are enabled.
4. Start the export once.
5. Wait for the whole package to finish before starting another export.

The single-page fallback is disabled, so wide panels must not be silently reduced to the first page.
