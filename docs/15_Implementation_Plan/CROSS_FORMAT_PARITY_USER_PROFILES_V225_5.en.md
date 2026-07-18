# v225.5 — Cross-format parity gate, legacy export retirement, and user profiles

## Goal

Make the physical page-aware package the only Professional Print Center source for SVG, PNG, PDF, DOCX, and HTML, automatically block format divergence, and add persistent safe A4/A3 profiles.

## Implementation

1. `VisualizationCrossFormatParityGate` compares page count, physical size, track partition, geometry signature, and canonical preview pages.
2. `VisualizationPageAwarePackage` v1.3 requires a successful parity gate for `export_ready`.
3. `UserPhysicalPrintProfileStore` persists user profiles in JSON between sessions.
4. User values cannot weaken baseline minimum font, line, or track floors.
5. Professional reports and LAS Viewer use `PageAwareStaticArtifact`.
6. Multi-page SVG/PNG is delivered as a manifest-backed ZIP; first-page fallback is forbidden.
7. Legacy CompositeLog static export is removed from the active path.
8. UI and documentation are synchronized in `ru/kk/en`.

## Definition of Done

- the parity gate blocks an invalid package;
- the UI exposes parity status and gate id;
- an A4/A3 user profile persists and controls layout;
- SVG/PNG never lose pages;
- tests, build metadata, and documentation match v225.5.
