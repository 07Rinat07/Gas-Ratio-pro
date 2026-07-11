# Presentation Export v27

`reports.presentation_export` writes a printable engineering HTML report from the shared `PresentationModel` and stores a JSON manifest next to the report.

The exporter does not recalculate intervals, evidence, confidence or recommendations. It consumes the same presentation model that is used by HTML, future PDF/DOCX renderers and UI screens.

## Purpose

- keep screen, print and export content synchronized;
- avoid rebuilding report sections separately for every export format;
- record which report profile was exported;
- provide a safe foundation for PDF/DOCX export.

## Files

A typical export package contains:

- `gas-ratio-professional-report.html` — printable engineering report;
- `gas-ratio-professional-report.manifest.json` — export metadata, table titles, figure count and report profile.

## Report profiles

The engineering profile remains the default. Technical diagnostics and raw calculation tables are still available through expert workflows, but they are not part of the primary report experience.
