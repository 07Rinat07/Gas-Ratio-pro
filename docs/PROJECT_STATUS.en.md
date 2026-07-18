# Current status — v225.5

Updated: 18 July 2026.

## Active stage

**Stage 4 — Workbench UI Completion / Stabilization & Release Audit.** Build status: **release candidate v225.5**.

## Implemented

- `VisualizationCrossFormatParityGate` automatically compares SVG, PNG, PDF, DOCX, and HTML;
- `VisualizationPageAwarePackage` v1.3 is ready only after the parity gate passes;
- Professional Print Center exposes the exact profile, pages, parity status, and gate id;
- persistent user A4/A3 physical profiles are available;
- minimum font, line, and track width are protected by baseline safety floors;
- professional report export and LAS Viewer use page-aware static delivery;
- multi-page SVG/PNG is delivered as a ZIP with `manifest.json`;
- legacy CompositeLog static export is retired;
- documentation is synchronized in Russian, Kazakh, and English.

## Release verification

Release-gate result:

- targeted renderer/export/UI set: **123 passed**;
- full regression suite: **2843 tests, 2792 passed, 51 failed**;
- all 51 failures reproduce on clean v225.4;
- new v225.5 regression failures: **0**;
- Python compileall, 108 relative Markdown links, and the documentation manifest: successful.

Known legacy regression failures are evaluated separately and are not hidden.

## Next stage

Complete Stage 4 through a real user acceptance path: create/select a profile, preflight preview, parity status, PDF/DOCX/HTML export, and multi-page SVG/PNG bundle delivery.
