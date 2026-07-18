# v225.6 Implementation Plan — Golden Artifacts, Print Center Acceptance, and Legacy Audit

## Goal

Freeze A4/A3 physical layout, exercise the real user export path, and convert 51 known failures into a controlled disposition registry.

## Completed

1. Added a ten-track fixture with interval overlays.
2. Generated SVG/PNG/PDF golden artifacts for four profiles.
3. Added generate/verify service and regeneration script.
4. Implemented an end-to-end acceptance runner with profile persistence.
5. Validated the HTML/PDF/DOCX bundle and multi-page SVG/PNG ZIP delivery.
6. Fixed raster preview scaling inside the actual PDF frame.
7. Classified all 51 legacy contracts without silent `xfail`.
8. Synchronized documentation and release metadata in three languages.

## Verification result

- 150 targeted tests pass.
- Full suite: 2853 tests, 2802 pass, 51 inherited failures.
- The registry and actual failure set match 1:1; there are no new regressions.
