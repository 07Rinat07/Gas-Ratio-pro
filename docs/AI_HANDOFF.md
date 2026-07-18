# Latest implementation — Cross-format parity, user profiles, and static-export retirement v225.5

## Runtime contracts

- `VisualizationPageAwarePackageBuilder` renders SVG, PNG, and PDF and then runs `VisualizationCrossFormatParityGate`.
- Package schema version is `1.3`; `export_ready` requires renderer QA and `parity_gate.ok`.
- The gate verifies layout/package/preview page counts, physical dimensions, actual PDF page count, PNG dimensions, track partition, and geometry signature.
- DOCX/HTML consume canonical preview `pages` and are represented in the same parity matrix.

## User profiles

- `UserPhysicalPrintProfileStore` persists `gas-ratio-pro.physical-print-profiles` in `data/user_preferences/physical_print_profiles.json`.
- Only A4/A3 user profiles are accepted.
- User values may increase readability floors or reduce page capacity, but cannot weaken the built-in baseline.
- Streamlit Professional Print Center can create, save, select, and apply these profiles.

## Static delivery

- `build_page_aware_static_artifact()` is the delivery boundary for professional SVG/PNG/PDF output.
- Multi-page SVG/PNG is a ZIP with `manifest.json` and one file per physical page.
- LAS Viewer uses the same delivery adapter.
- `reports.export_static` now handles genuine Plotly/Kaleido output only; legacy CompositeLog static export is explicitly retired.

## Release governance

- Build: `v225.5`, channel `release-candidate`.
- Always update and verify Russian, Kazakh, and English README, user instructions, developer architecture, status, roadmap, project plan, changelog, release notes, and documentation manifest.
