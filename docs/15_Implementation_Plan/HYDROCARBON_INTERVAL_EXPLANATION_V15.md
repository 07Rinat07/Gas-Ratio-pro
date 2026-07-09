# Hydrocarbon Interpretation Engine v15 — Interpretation Explanation Engine

## Status

Implemented.

## Purpose

Version v15 adds the engineer-facing `InterpretationExplanation` model. The interval engine no longer exposes only a fluid class and confidence score. Each interval now carries a concise explanation package that can be used directly by UI interval cards, executive summaries, PDF/DOCX reports and future API consumers.

Project principle:

> Каждая интерпретация должна быть понятной, объяснимой и воспроизводимой.

## New model

`InterpretationExplanation` contains:

- `summary` — short cautious engineering conclusion.
- `classification` — display classification such as gas, oil, condensate, transition or uncertain interval.
- `decision_level` — `very_high`, `high`, `medium`, `low`, `review`, `unknown`.
- `reasoning` — compact reasoning chain from depth, confidence, rules and geological context.
- `supporting_evidence` — selected evidence from Pixler, Haworth, project indicators and classification records.
- `limitations` — explicit limitations such as incomplete data, single-sample interval, missing ratio values or weak geological support.
- `recommendations` — practical next actions for the engineer.
- `references` — source/method references collected from the evidence records.
- `engineering_hypothesis` — always true for this preliminary interpretation layer.

## Design rule

The Explanation Engine does not calculate new geochemical parameters. It converts existing interval data into a clear interpretation package using:

- interval model;
- rule traces;
- evidence items;
- method registry references;
- data confidence;
- geological confidence;
- interpretation context;
- quality flags.

## Engineer-facing wording

Reports and UI should avoid categorical statements such as “газовая залежь доказана”. Preferred wording:

- “Признаки соответствуют вероятному газонасыщенному интервалу.”
- “Интерпретация предварительная.”
- “Требуется подтверждение по данным ГИС, керна, испытаний и бурового контекста.”

## API impact

The public interval rows now include:

- `explanation`;
- `explanation_summary` in summary and marker payloads;
- `explanation_model` in the API contract;
- `build_interpretation_explanation` as a public builder.

Downstream modules must consume the explanation object instead of generating their own reasoning text from private fields.

## Next step

After v15, the remaining HIE work is final regression, architecture audit and `Hydrocarbon Interpretation Engine v1.0` freeze.
