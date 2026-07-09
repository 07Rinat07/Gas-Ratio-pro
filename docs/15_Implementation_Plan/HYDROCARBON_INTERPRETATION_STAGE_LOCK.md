# GAS RATIO PRO — Hydrocarbon Interpretation Stage Lock

## Purpose

This document freezes the next development order so the project does not jump between unrelated modules.
Each stage must be completed, tested and accepted before the next stage starts.

## Current Locked Priority

The current priority is not general UI polishing and not geological modeling.
The current priority is the full hydrocarbon interpretation pipeline:

```text
LAS data
  -> curve validation
  -> gas ratio calculation
  -> hydrocarbon interval detection
  -> interval classification
  -> interpretation text
  -> marked graph model
  -> printable report model
  -> export / print
```

## Development Rule

One module is considered active at a time.
A new module may start only after the active module reaches Definition of Done.

The development order is:

1. Hydrocarbon Interval Engine
2. Interpretation Engine
3. Marked Graph Report
4. Professional Report Engine
5. PDF / DOCX / XLSX Export
6. Petrophysics Engine
7. Toolbar and Unified Design System
8. Geological Modeling

## Stage 1 — Hydrocarbon Interval Engine

### Goal

Find all meaningful intervals with hydrocarbon indicators, not only the strongest few.
The module must create one shared interval model used by Pixler, reports, graphs, exports and interpretation.

### Required output model

Each interval must contain:

- top depth;
- bottom depth;
- thickness;
- fluid type;
- confidence;
- evidence list;
- source curves;
- calculated gas-ratio indicators;
- warnings;
- merge/split metadata;
- report-ready labels.

### Required classifications

- Gas;
- Oil;
- Gas condensate;
- Mixed;
- Possible hydrocarbon;
- Water / non-pay;
- Uncertain.

### Must be completed before moving on

- interval detection from available LAS/gas-ratio data;
- inclusive detection so weaker but meaningful intervals are not lost;
- merge adjacent intervals using configurable depth gap;
- split intervals when fluid classification changes;
- store result in a shared report-ready data model;
- expose output to Pixler and report modules;
- tests for detection, merge, split, classification and serialization.

## Stage 2 — Interpretation Engine

### Goal

Generate readable engineering interpretation for each interval.

### Must explain

- why the interval was selected;
- which indicators support gas/oil/mixed classification;
- confidence level;
- data quality warnings;
- what should be checked by the interpreter.

## Stage 3 — Marked Graph Report

### Goal

Show detected intervals directly on LAS graphs.

### Required graph elements

- depth scale;
- selected curves;
- colored hydrocarbon zones;
- top/bottom markers;
- interval labels;
- legend;
- export-ready figure package.

## Stage 4 — Professional Report Engine

### Goal

Generate a clean printable engineering report instead of a raw technical dump.

### Required sections

- title page;
- project/well summary;
- methods used;
- hydrocarbon interval table;
- interpretation per interval;
- marked graphs;
- warnings and limitations;
- final conclusion.

## Stage 5 — Export and Print

### Goal

HTML remains preview/debug format. PDF becomes the main printable format.

### Required formats

- PDF;
- DOCX;
- XLSX;
- HTML preview;
- PNG/SVG graph assets.

## Stage 6 — Petrophysics Engine

### Goal

Connect hydrocarbon intervals with reservoir quality and petrophysical indicators.

### Required calculations

- porosity;
- shale volume;
- water saturation;
- hydrocarbon saturation;
- net reservoir;
- net pay;
- net/gross;
- reservoir quality class;
- cutoff logic.

## Stage 7 — Toolbar and Unified Design System

### Goal

Make the application look and behave like one professional engineering platform.

### Required UI actions

- Open LAS;
- Validate;
- Detect HC Intervals;
- Interpret;
- Plot Markers;
- Petrophysics;
- Modeling;
- Report;
- Export;
- Print.

## Stage 8 — Geological Modeling

### Goal

Use interpreted intervals and petrophysical results as input for multi-well interpretation and modeling.

### Scope

- correlation markers;
- zones;
- fluid contacts;
- reservoir intervals;
- property modeling input;
- future 2D/3D model support.

## Definition of Done for each stage

A stage is finished only if:

- code is implemented through UI -> Controller -> Service -> Repository -> Storage;
- tests are added or updated;
- documentation is updated;
- output is visible in UI or export layer;
- no unrelated module is started in the same step;
- release ZIP excludes `.git`, `.venv`, caches, logs and generated debug artifacts.


## Current implementation update — Hydrocarbon Interval Engine v4

The active stage remains Hydrocarbon Interval Engine. This step refines the shared interval classification model without starting the next module.

Implemented in this step:

- schema updated to `gas-ratio-pro/hydrocarbon-intervals/v4`;
- directional mixed fluid classes added:
  - `gas_oil`;
  - `oil_gas`;
- `water` classification added as non-prospective interval type;
- `uncertain` classification added as low-confidence candidate type;
- marker style mapping extended for new classes;
- ratio-conflict fallback added for rows where Pixler, Oil Indicator and Haworth signs disagree;
- tests added for directional gas/oil labels, uncertain candidates and water exclusion.

Validation:

- compileall: PASS;
- pytest: 1041 passed / 0 failed.
