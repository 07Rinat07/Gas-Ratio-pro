# Hydrocarbon Interpretation Engine v16 — Recommendation & Limitation Engine

## Purpose

Version v16 formalizes the last engineer-facing part of the interpretation core before the final freeze: recommendations and limitations are no longer only free text. They are exported as structured, auditable objects that reports, interval cards, PDF/DOCX exporters and expert views can consume without re-parsing notes.

Project principle:

> Каждая интерпретация должна быть понятной, объяснимой и воспроизводимой.

## New models

### `InterpretationLimitation`

Fields:

- `category` — data quality, geological context, calculation, interval geometry, confidence, professional caution;
- `severity` — `info`, `medium`, `high`;
- `message` — concise engineer-facing limitation text;
- `source` — source of the limitation, for example `quality_flag:single_sample_interval` or `data_confidence_score`;
- `recommendation` — practical verification action connected to the limitation.

### `InterpretationRecommendation`

Fields:

- `priority` — `low`, `medium`, `high`;
- `action` — practical next action;
- `reason` — why this action is proposed;
- `target` — default `interval`;
- `source` — rule trace, confidence level or limitation source.

## Public builders

- `build_interpretation_limitations(interval)`
- `build_interpretation_recommendations(interval)`

These builders are now part of the public Hydrocarbon Interval Engine API contract. Downstream modules must use them or consume the exported explanation payload instead of duplicating recommendation logic.

## Explanation integration

`InterpretationExplanation` keeps the existing simple fields:

- `limitations`
- `recommendations`

and now additionally exports:

- `structured_limitations`
- `structured_recommendations`

This keeps backward compatibility for simple reports while enabling expert reports and UI panels to show severity, source and reason.

## Reporting rule

Default engineer-facing reports should show only short limitation/recommendation messages. Expert/technical appendices may show the full structured fields including category, severity, source and reason.

## Schema

Hydrocarbon interval schema updated to:

`gas-ratio-pro/hydrocarbon-intervals/v16`

## Next step

After v16, the remaining work before `Hydrocarbon Interpretation Engine v1.0` is:

1. final regression suite;
2. architecture audit;
3. documentation consistency check;
4. v1.0 freeze.
