# Hydrocarbon Interval Engine v13 — Interpretation Context Engine

## Purpose

v13 adds `Interpretation Context Engine` to keep geological and data-quality context inside the Hydrocarbon Interval Engine. Reports, plots, UI and future PDF/DOCX exporters must consume this context instead of reconstructing geological meaning from raw rows.

Project principle:

> Каждая интерпретация должна быть понятной, объяснимой и воспроизводимой.

## Added models

### HydrocarbonInterpretationContext

Stores practical interpretation context for each interval:

- top / base / thickness;
- dominant lithology;
- barrier above / barrier below;
- gas trend;
- curve quality;
- missing curves;
- noise level;
- neighbor summary;
- formation;
- well name.

### Confidence split

Each interval now exposes:

- `data_confidence_score` — confidence from evidence, quality flags and rules;
- `geological_confidence_score` — confidence from lithology, barriers, continuity and trend;
- `decision_level` — engineer-facing level: `very_high`, `high`, `medium`, `low`, `review`, `unknown`.

The original `confidence_score` remains available for backward compatibility and currently represents data/evidence confidence.

### Evidence tree

Each interval now exports grouped explanation blocks:

- Gas ratios;
- Project indicators;
- Geological context;
- Applied rules;
- Confidence factors.

This structure is intended for future UI cards and report sections where the engineer can expand an interval and see why it was interpreted that way.

## Barrier and neighbor awareness

After all intervals and lithological barriers are detected, the engine enriches intervals with neighbor context:

- nearest barrier above;
- nearest barrier below;
- neighboring productive interval above/below.

This supports correct reporting of separated productive packs without merging through Claystone or other tight barriers.

## API contract update

Schema updated to:

```text
gas-ratio-pro/hydrocarbon-intervals/v13
```

The public payload now includes context fields and evidence tree. Downstream layers must not duplicate interval interpretation logic.

## Next step

After v13 the remaining tasks before Hydrocarbon Interval Engine v1.0 are:

1. final API freeze;
2. expanded validation dataset;
3. documentation polish;
4. transition to Professional Reporting System.
