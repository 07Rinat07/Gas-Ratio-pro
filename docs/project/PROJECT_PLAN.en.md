# Gas Ratio Pro project plan

Updated: 18 July 2026. Active build: `v225.3`.

## Mandatory engineering principles

- engineering data, tracks, and scales are never reduced merely to fit printing;
- UI, PDF, DOCX, SVG, and PNG use renderer-neutral contracts;
- one pipeline is the only source of page geometry;
- A4/A3 use physical parameters and minimum readable typography;
- export starts with one action and blocks duplicate runs until the whole package is complete;
- user and developer instructions are updated consistently in Russian, Kazakh, and English.

## Completed stage — v225.3

- shared page-space headers, footers, and numbering;
- repeated legend from the renderer-neutral label/legend model;
- geometry signature v3;
- page-aware package v1.1;
- localized Print Center summary;
- LAS Viewer SVG/PDF/PNG through one package;
- QA covers render-model and page-chrome primitives.

## Next increment — Visible Print Center Integration

1. Show the physical profile and exact page count in Professional Print Center before launch.
2. Pass the existing page-aware output contract to PDF, DOCX, SVG, and PNG.
3. Connect `page_svgs` to DOCX/HTML without rebuilding layout.
4. Keep duplicate-run protection active for the complete package.
5. Remove independent Plotly/static fallback branches after confirmed parity checks.
6. Update code, tests, README files, instructions, status, changelog, and plans in `ru / kk / en`.
