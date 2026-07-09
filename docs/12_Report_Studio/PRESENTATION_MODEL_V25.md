# Presentation Model v25

`PresentationModel` is the single presentation source for engineer-facing reports,
plots, UI cards and future PDF/DOCX exporters.

## Purpose

The reporting layer must not rebuild the same interpretation several times for
HTML, plot, PDF and screen widgets. All renderers should consume one composed
presentation object built from the frozen Hydrocarbon Interpretation Engine
result.

## Contents

- `HydrocarbonIntervalResult` from the interpretation engine.
- `ExecutiveSummary` for first-page engineering conclusions.
- `IntervalReportCard` items for interval cards.
- Engineer-first report tables.
- Expert/appendix tables.
- Optional `WellLogPlotResult` for professional tablets.
- `PresentationMetadata` for report headers.

## Rule

Renderers may format the data, but they must not recalculate fluid type,
confidence, explanation, recommendations or limitations independently.
