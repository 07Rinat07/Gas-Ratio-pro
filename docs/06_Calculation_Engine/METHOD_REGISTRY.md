# Method Registry and Provenance Policy — v225.9

## Purpose

GAS RATIO PRO must explain every engineering calculation used in interpretation and reporting. No new formula, threshold family, or petrophysical method may enter production logic without a machine-readable method profile and validation evidence.

## Registries

- Mud-gas and interval methods remain exposed through `core.method_registry`.
- The Stage 5 petrophysical registry is `config/petrophysical_method_registry_v225_9.json`.
- The petrophysical registry is frozen by `gas-ratio-pro/petrophysical-method-registry/v1` and contains 10 methods.

## Required fields

Every petrophysical method contains:

- method ID, display name, category, and exact production implementation path;
- short equation or deterministic rule;
- audit status and final-report policy;
- source ID, title, authors, year, source type, legal status, and citation note;
- input, parameter, and output unit contracts;
- applicability domain and limitations;
- reference dataset IDs;
- absolute/relative numerical tolerance;
- uncertainty metadata.

## Registered petrophysical methods

| Method ID | Policy | Validation |
| --- | --- | --- |
| `petrophysics.vsh_gr_linear` | warning | synthetic GR endpoints |
| `petrophysics.vsh_gr_larionov_tertiary` | warning | synthetic IGR vector |
| `petrophysics.vsh_gr_larionov_old_rocks` | warning | synthetic IGR vector |
| `petrophysics.vsh_gr_clavier` | warning / source review required | synthetic IGR vector |
| `petrophysics.phie_shale_correction` | warning | synthetic POR/VSH vector |
| `petrophysics.sw_archie` | warning | synthetic PHIE/RT vector |
| `petrophysics.sw_simandoux` | warning | synthetic PHIE/RT/VSH vector |
| `petrophysics.sw_indonesia` | warning | synthetic PHIE/RT/VSH vector |
| `petrophysics.sw_dual_water_foundation` | **blocked final report** | numerical foundation only |
| `petrophysics.net_pay_cutoff_flags` | warning | synthetic cutoff classification |

## Validation rule

`PetrophysicalValidationApplicationService` executes the public production functions against static synthetic reference cases. Structural, unit, provenance, tolerance, and numerical mismatches block the gate. Numerical reproducibility does not automatically grant final-report permission.

## Copyright and patent handling

The project stores short equations, bibliographic metadata, synthetic examples, and original implementation code. It does not reproduce protected charts, tables, interpretation plates, or long source text. Field/corporate datasets require explicit data-rights records before entering validation.
