# Method Registry and Provenance Policy

## Purpose

GAS RATIO PRO must be able to explain every engineering calculation used in hydrocarbon interval detection, reporting and future petrophysical interpretation.

No new calculation formula, threshold family or interpretation method should be added to production logic without a registered method profile.

## Required registry fields

Each method profile must contain:

- method id;
- public/project method name;
- authors or project owner;
- year or project version;
- source title;
- source type;
- audit status;
- implementation status;
- scope of use;
- limitations;
- citation / copyright note.

## Current implemented registry entries

| Method ID | Method | Authors / owner | Status | Use |
| --- | --- | --- | --- | --- |
| `haworth_mud_gas` | Haworth mud-gas ratios | Haworth, Sellens, Whittaker | `verified_public_reference` | Wh, Bh and Ch interval evidence. |
| `pixler_gas_ratio` | Pixler hydrocarbon gas ratios | B. O. Pixler | `verified_public_reference` | C1/C2 and C1/C3 supporting fluid-character evidence. |
| `project_oil_indicator` | Project oil/gas indicator | GAS RATIO PRO project | `project_engineering_hint` | Internal supporting oil/gas tendency indicator. |
| `hydrocarbon_interval_engine` | GAS RATIO PRO Hydrocarbon Interval Engine | GAS RATIO PRO project | `project_engineering_hint` | Rule-based grouping, classification, evidence and confidence packaging. |

## Provenance rule

Every interval evidence item should carry:

- `method_id`;
- `source_id`;
- method name;
- parameter;
- value;
- status;
- source title;
- authors;
- limitations.

This allows reports, QA tools and future PDF/DOCX exporters to trace each interval conclusion back to its calculation source without copying copyrighted source material.

## Copyright and patent handling

The project may store short equations, method names, bibliographic metadata and original implementation code. The project must not copy protected charts, interpretation plates, tables, figures or long text fragments from copyrighted publications unless explicit permission exists.

Published methods must be cited. Internal engineering hints must be clearly labelled as internal and preliminary.
