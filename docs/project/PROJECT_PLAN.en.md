# Gas Ratio Pro project plan

Updated: 18 July 2026. Active build: `v225.4`.

## Mandatory engineering principles

- one pipeline is the only source of page geometry;
- UI, PDF, DOCX, HTML, SVG, and PNG use renderer-neutral contracts;
- A4/A3 and user profiles preserve minimum readable typography;
- multi-page preview cannot silently collapse to page one;
- documentation and instructions remain synchronized in `ru / kk / en`.

## Completed stage — v225.4

- visible Print Center connected to the physical package;
- per-page preview and exact preflight summary added;
- page-aware package v1.2 and preview contract v1.1;
- direct multi-page preview for DOCX/HTML;
- shared strict normalizer for HTML/DOCX/PDF/assets;
- localized labels and messages;
- `bundle` uses the same payload.

## Next approved increment — Parity Gate & Legacy Export Retirement

1. Build an automated parity matrix for UI, PDF, DOCX, HTML, SVG, and PNG.
2. Verify A4/A3, both orientations, track partition, page count, geometry signature, and page chrome.
3. Remove independent static/Plotly fallback branches only after parity passes.
4. Add validated user-defined physical profiles with minimum-size floors.
5. Update tests and all documentation in three languages.

## Definition of Done

- the physical package is visible before launch;
- all formats consume the canonical `pages` contract;
- no downstream layout rebuild exists;
- no single-page fallback exists;
- parity is proven with tests and reference artifacts;
- version metadata, README, instructions, status, roadmap, changelog, and manifest are synchronized.
