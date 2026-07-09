# Formula Source Audit — Mud Gas and Petrophysics

## Purpose

This document records the formula/source audit for calculation modules. Every formula used by GAS RATIO PRO must have one of these statuses:

- `verified_public_reference` — formula is implemented from an openly published reference and cited.
- `project_engineering_hint` — formula is used only as a preliminary engineering indicator and must not be treated as final interpretation.
- `draft_requires_validation` — formula or threshold is not allowed for final reports until validated.
- `internal_method_required` — formula must be provided by the user/company and documented separately.

## Copyright and patent handling

- The project stores formula names, short equations, bibliographic references and own implementation code.
- The project must not copy full papers, copyrighted tables, figures, charts or proprietary interpretation plates without permission.
- Published equations and numerical guidelines are cited to their authors; the implementation remains original project code.
- Before commercial distribution, patented/proprietary workflows must receive a separate freedom-to-operate review.
- If a method is only available from a copyrighted paper, the project cites it and uses a short paraphrased description rather than reproducing protected material.

## Audited formulas

| Area | Formula / method | Current implementation | Status | Source note |
| --- | --- | --- | --- | --- |
| Mud gas | `Wh = (C2 + C3 + ΣC4 + ΣC5) / ΣC * 100` | `core.calculations`, `las_editor.mud_gas_interpretation` | `verified_public_reference` | Haworth/Sellens/Whittaker method as summarized in mud-gas literature. |
| Mud gas | `Bh = (C1 + C2) / (C3 + ΣC4 + ΣC5)` | `core.calculations`, `las_editor.mud_gas_interpretation` | `verified_public_reference` | Haworth Balance Ratio. |
| Mud gas | `Ch = (ΣC4 + ΣC5) / C3` | `core.calculations`, `las_editor.mud_gas_interpretation`, curve templates | `verified_public_reference` | Previous unverified expression was removed from the main calculation path. |
| Mud gas | Pixler ratios `C1/C2`, `C1/C3`, `C1/ΣC4`, `C1/ΣC5` | `core.calculations`, templates/report logic | `verified_public_reference` | Pixler 1969 hydrocarbon ratio method. |
| Mud gas | Oil indicator `(C3 + ΣC4 + ΣC5) / C1` | `core.calculations`, `las_editor.mud_gas_interpretation` | `project_engineering_hint` | Literature notes that the origin is not fully explained; use only as supporting evidence. |
| Petrophysics | Archie water saturation | `las_editor.petrophysical_workspace` | `verified_public_reference` | Clean-formation equation; requires calibrated `Rw`, `a`, `m`, `n`. |
| Petrophysics | Simandoux shaly-sand saturation | `las_editor.advanced_saturation_models` | `project_engineering_hint` | Implementation uses a quadratic conductivity form; requires calibration and source review before final reserves work. |
| Petrophysics | Indonesia saturation | `las_editor.advanced_saturation_models` | `project_engineering_hint` | Approximation for shaly formations; requires calibration. |
| Petrophysics | Dual Water | `las_editor.advanced_saturation_models` | `draft_requires_validation` | Current implementation is a transparent foundation approximation, not the full proprietary/standard Dual Water workflow. |

## Required project rules

1. Final reports must label mud-gas interpretation as preliminary unless confirmed by well logs, lithology, tests and operational context.
2. Thresholds for Pixler/Haworth zones must remain configurable and source-tagged.
3. Any corporate/internal interpretation chart must be added as a separate method profile, not mixed into public formulas.
4. PDF/report text must include a short bibliography section for formulas used in that report.
5. If a formula lacks source attribution, it cannot be used for final printable conclusions.

## Next audit actions

- Add source IDs to every report manifest.
- Add UI warnings for `project_engineering_hint` and `draft_requires_validation` methods.
- Add regression tests proving that `CH` equals `(ΣC4 + ΣC5) / C3` in both calculation paths.
- Keep all productive intervals separated across explicit Clay/Claystone/Tight barrier gaps.

## Method Registry update

Hydrocarbon Interval Engine now links structured interval evidence to `core.method_registry`.

Implemented profiles:

- `haworth_mud_gas` — Haworth mud-gas ratios used for Wh, Bh and Ch evidence;
- `pixler_gas_ratio` — Pixler hydrocarbon gas ratios used for C1/C2 and C1/C3 evidence;
- `project_oil_indicator` — internal project engineering hint, not a standalone published method;
- `hydrocarbon_interval_engine` — internal rule engine combining sourced indicators, quality flags and lithology/barrier context.

Rule: any new formula or interpretation method must be registered before it is used in report-facing calculations.
