# Latest implementation — Physical golden baseline and Print Center acceptance v225.6

## Physical golden contract

- `VisualizationPhysicalGoldenArtifactService` owns generate/verify for A4/A3 portrait/landscape.
- Approved artifacts live in `tests/fixtures/physical_golden_artifacts/`.
- Source fixture: `tests/fixtures/visualization/reference_physical_ten_tracks.json`.
- Regenerate only after visual review with `python scripts/regenerate_physical_golden_artifacts.py`.
- The manifest locks SVG/PNG checksums, PDF checksum, dimensions, page count, track partition, chrome count, geometry signature, and parity gate id.

## Print Center acceptance

- `ProfessionalPrintCenterAcceptanceRunner` executes profile persistence, page-aware preparation, visible view model, bundle export, bundle validation, and SVG/PNG delivery.
- Evidence is `print-center-acceptance-report.json`.
- `_AutoScaleRasterImage` in `reports/presentation_pdf.py` scales preview images against the actual ReportLab frame and fixes mixed-orientation overflow.

## Legacy regression audit

- `config/legacy_regression_contracts_v225_6.json` contains all 51 inherited v225.4/v225.5 failures.
- Categories: obsolete version identity, brittle UI source assertion, visual rebaseline, architecture boundary, behavioral compatibility.
- Silent `xfail` and test deletion without replacement are forbidden.
- Architecture debt remains release-visible.

## Release governance

- Build: `v225.6`, channel `release-candidate`.
- User release archives must exclude `.github/workflows` unless local build/runtime explicitly requires them.
- Always update and verify Russian, Kazakh, and English README, user instructions, developer architecture, status, roadmap, project plan, changelog, release notes, and documentation manifest.
