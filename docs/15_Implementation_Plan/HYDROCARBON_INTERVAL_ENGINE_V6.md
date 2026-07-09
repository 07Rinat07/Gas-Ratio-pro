# Hydrocarbon Interval Engine v6 — Lithology & Barrier Awareness

## Status

Active module: **Hydrocarbon Interval Engine**.

This document updates the stage-locked implementation plan. The project must finish the interval engine before starting the next major module.

## Purpose

Version v6 extends hydrocarbon interval detection with a separate lithology/barrier model. Productive intervals remain factual and separated. Claystone, shale, clay or tight barriers are not merged into neighbouring gas or oil intervals.

## Terminology

| Term | Project meaning |
|---|---|
| Clay | Unconsolidated clay / глина |
| Claystone | Argillite / indurated clay-rich rock / аргиллит, глинистая порода |
| Shale | Shale / глинистый сланец |
| Tight interval | Dense low-permeability interval / плотный интервал |
| Barrier | Non-productive separator / непроницаемая или условно непроницаемая перемычка |

Project reports should use `Claystone`, not `Argillite`, in English output.

## Data model

The interval result now contains two separate collections:

1. `intervals` — productive or potentially productive hydrocarbon intervals.
2. `barriers` — non-productive lithological separators.

This prevents distortion of top/base depths. For example:

```text
2148.2-2150.0  Gas
2150.0-2150.2  Claystone barrier
2150.2-2154.8  Gas
```

must remain two gas intervals separated by one barrier, not one merged gas interval.

## Rule

Default behavior:

```text
preserve_explicit_gaps = True
```

The engine may compute total net pay separately in future modules, but must not join factual interval boundaries across lithological barriers by default.

## Report behavior

Reports may include an additional table:

```text
Литологические перемычки между интервалами
```

This table is informational. It does not replace the hydrocarbon interval table and does not mark a barrier as productive.

## Remaining work inside this module

Before moving to Interpretation Engine, finish:

1. Evidence Engine — structured evidence objects, not only printable strings.
2. Confidence Engine — formula-based confidence from independent signals and data quality.
3. Quality Flags — noisy interval, insufficient curves, uncertain boundary, possible false positive.
4. Acceptance tests using real LAS-derived examples.

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

