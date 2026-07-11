# Presentation Layer v1 Freeze

## Purpose

This document records the freeze gate for the first stable Presentation Layer.
The layer is responsible for presenting already interpreted engineering content;
it must not run hydrocarbon interpretation, recalculate gas-ratio formulas or
choose a different interval list per output format.

## Frozen flow

```text
PresentationModel
        ↓
EngineeringDocument
        ↓
HTML / PDF / DOCX / future UI
```

## Freeze rules

1. `PresentationModel` is the single presentation source.
2. `EngineeringDocument` is the single renderer-neutral document model.
3. HTML, PDF and DOCX renderers must preserve the same profile, table titles and plot count.
4. The default engineering profile must remain engineer-first: conclusions, intervals,
   confidence, recommendations and limitations before technical diagnostics.
5. Technical tables and diagnostics remain available through expert/appendix workflows.
6. Renderers must not call calculation engines, rule engines or interval detection.

## Freeze gate

The freeze gate is implemented in:

```text
reports/presentation_freeze.py
```

The public entry point is:

```python
build_presentation_freeze_status(model).require_frozen()
```

## Status after v33

`Presentation Layer v1` is ready for use as the stable foundation for the next module:

```text
Modern UI / Workspace integration
```

Future rendering improvements, such as embedding real plot images into PDF/DOCX,
should extend renderer backends without changing the presentation contract.
