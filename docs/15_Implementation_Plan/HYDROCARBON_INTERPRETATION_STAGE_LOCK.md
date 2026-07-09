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

## Current implementation update — Hydrocarbon Interval Engine v5

The active stage remains Hydrocarbon Interval Engine. This step fixes the interval continuity policy and geological terminology before any report or petrophysics stage continues.

Implemented in this step:

- schema updated to `gas-ratio-pro/hydrocarbon-intervals/v5`;
- explicit interval gaps are preserved by default;
- hydrocarbon intervals are no longer automatically merged across explicit non-reservoir gaps;
- merge across explicit gaps remains possible only through an explicit rule override: `preserve_explicit_gaps=False`;
- interval rows now expose source row coverage metadata;
- report table rows expose `source_start_row`, `source_end_row` and `separated_by_gap`;
- terminology is fixed for lithological barriers:
  - `Clay` means глина;
  - `Claystone` means аргиллит / глинистая порода;
  - `Shale` means глинистый сланец;
  - `Tight barrier` means плотная непроницаемая перемычка.

Geological rule:

Productive intervals separated by a clay, claystone, shale or tight barrier interval must be reported as separate intervals by default. The engine may calculate total net pay separately, but it must not distort real tops and bases by joining intervals across barriers.

Accepted reporting example:

```text
2148.2-2150.0  Gas
2150.0-2150.2  Claystone / Tight barrier
2150.2-2154.8  Gas
```

The two gas intervals remain separate productive intervals in the report.

---

## Current implementation update — Hydrocarbon Interval Engine v6

Hydrocarbon Interval Engine v6 adds lithology and barrier awareness.

Implemented rules:

- productive intervals remain separated across explicit Clay / Claystone / Shale / Tight barrier intervals;
- the result object now stores `barriers` separately from `intervals`;
- report payloads can include a dedicated lithological barrier table;
- English output uses `Claystone` for аргиллит / глинистая порода;
- `Argillite` should not be used as the preferred project output term.

Current schema:

```text
gas-ratio-pro/hydrocarbon-intervals/v6
```

Next work remains inside Hydrocarbon Interval Engine:

1. structured evidence model;
2. confidence scoring;
3. quality flags;
4. acceptance tests on real project datasets.

## Hydrocarbon Interval Engine v7 — Structured Evidence and Quality Flags

The active interval model now separates printable evidence from machine-readable evidence.
Every interpreted interval may expose:

- `evidence_items` — structured method/parameter/value/direction/weight records;
- `quality_flags` — machine-readable QA markers such as `single_sample_interval`,
  `limited_numeric_evidence`, `no_numeric_gas_ratios`, `contains_missing_ratio_values`,
  and `uncertain_fluid_character`;
- legacy printable `evidence` strings remain available for current HTML/report tables.

This keeps the Hydrocarbon Interval Engine as the single source of truth for later
Interpretation Engine, graph markers, PDF reports and dashboards. Report modules must
consume the existing interval model and must not recalculate their own evidence.


## Hydrocarbon Interval Engine v8 — Confidence Scoring

The active stage remains **Hydrocarbon Interval Engine**.

This step adds transparent, evidence-based confidence scoring to the interval model.
Confidence is no longer only a text label. Each interval now carries:

- `confidence_score` — numeric engineering confidence from 0 to 100;
- `confidence` — stable label derived from score: low / medium / high;
- `confidence_factors` — machine-readable list of bonuses and penalties;
- quality penalties from `quality_flags`;
- support from structured evidence such as Haworth, Pixler and project oil indicator values.

Important rule:

> Confidence score is not an economic probability and does not prove commercial productivity. It only describes how consistently the available mud-gas indicators support the current interval classification.

The module still preserves separated hydrocarbon intervals across explicit gaps and lithological barriers such as Claystone, Shale or tight intervals.

Next work remains inside Hydrocarbon Interval Engine:

1. finish confidence scoring tests on real LAS examples;
2. validate weak, uncertain and water cases;
3. prepare Definition of Done checklist for this module before moving to Interpretation Engine.

## Hydrocarbon Interval Engine v9 — Method Registry and Evidence Provenance

The active stage remains **Hydrocarbon Interval Engine**.

This step adds method registry and provenance metadata to interval evidence.

Implemented:

- `core.method_registry` with auditable method profiles;
- evidence-level `method_id` and `source_id`;
- report/table payload field `evidence_provenance`;
- registered profiles for Haworth mud-gas ratios, Pixler gas ratios, internal oil indicator and the Hydrocarbon Interval Engine itself;
- project rule: no report-facing formula should enter production logic without a registry entry.

Current schema:

```text
gas-ratio-pro/hydrocarbon-intervals/v9
```

Next work remains inside Hydrocarbon Interval Engine:

1. validate Method Registry coverage for all current interval evidence;
2. add real-LAS acceptance tests for weak / uncertain / water / barrier cases;
3. prepare Definition of Done checklist before moving to Interpretation Engine.
