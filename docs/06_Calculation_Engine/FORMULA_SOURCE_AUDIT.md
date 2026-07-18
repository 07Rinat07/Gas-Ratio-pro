# Formula Source Audit — Mud Gas and Petrophysics v225.9

## Status vocabulary

- `verified_public_reference` — bibliographic source is recorded and the implementation is original project code.
- `project_engineering_hint` — transparent internal rule, usable only with a warning and calibration.
- `draft_requires_validation` — numerical comparison is allowed, but final-report use is blocked.
- `blocked_final_report` — application-service authorization must reject final engineering export.

## Petrophysical audit

| Method | Production implementation | Source/provenance state | Report policy |
| --- | --- | --- | --- |
| Linear Vsh | `calculate_shale_volume` | transparent project normalization | warning |
| Larionov Tertiary / old rocks | `calculate_shale_volume` | published empirical correlations; local calibration required | warning |
| Clavier Vsh | `calculate_shale_volume` | source review remains open | warning |
| Effective porosity correction | `calculate_effective_porosity` | transparent project foundation rule | warning |
| Archie Sw | `calculate_archie_water_saturation` | G. E. Archie, 1942, DOI `10.2118/942054-G` | warning |
| Simandoux Sw | `calculate_simandoux_water_saturation` | P. Simandoux, 1963 | warning |
| Indonesia Sw | `calculate_indonesia_water_saturation` | A. Poupon and J. Leveaux, 1971 | warning |
| Foundation Dual Water | `calculate_dual_water_saturation` | internal approximation inspired by Dual Water concepts, not the published full model | **blocked final report** |
| Reservoir/net/pay flags | `calculate_net_pay_flags` | explicit project cutoffs | warning |

## Stage 5 evidence

- Registry: `config/petrophysical_method_registry_v225_9.json`.
- Reference cases: `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json`.
- Gate evidence: `artifacts/validation/petrophysical_validation_v225_9.json`.
- Current numerical result: 10/10 methods pass; 9/10 are final-report eligible.

## Non-negotiable rules

1. Formula changes require a new or revised method record, source/legal review, units, expected results, tolerance, and passing evidence.
2. UI requests cannot alter calculation formulas.
3. Synthetic software references do not replace field calibration.
4. Final reports must reject `blocked_final_report` methods.
5. Interpretation 2.0 and controlled visual baselines remain frozen unless separate evidence is approved.
