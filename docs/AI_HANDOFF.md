# Latest implementation — Petrophysical Engine Validation Foundation v225.9

## Release state

- Build: `v225.9`.
- Channel: `stable`.
- Stage 5 foundation is complete.
- Numerical validation: **10/10 passed**.
- Final-report eligible: **9/10**.
- Full regression: **2881/2881 passed**.
- Live Workbench Acceptance: **14/14 passed**.
- Adaptive A3 landscape report acceptance: **4/4 passed**.

## Architecture

- `config/petrophysical_method_registry_v225_9.json` is the method/provenance/unit policy.
- `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json` contains synthetic expected-result cases.
- `core/petrophysical_validation_contract.py` validates schemas, units, uncertainty metadata, and fingerprints.
- `services/petrophysical_validation_application_service.py` executes production functions and enforces final-report policy.
- `scripts/run_petrophysical_validation_gate.py` writes machine-readable evidence.
- Report renderers use actual available page/section frames; `print-readability/v1.1` and `config/visual_rebaseline_contracts_v225_9.json` protect A3 landscape full-frame layout.

## Critical policy

`petrophysics.sw_dual_water_foundation` is numerically reproducible but `blocked_final_report`. Do not relabel it as the full Dual Water model. Formula changes require method provenance, legal/source review, a reference dataset, units, tolerance, uncertainty metadata, and passing evidence.

## Next authorized stage

Stage 5.1 — field-owned calibration datasets, sensitivity/uncertainty envelopes, read-only diagnostics, and final-export authorization integration. Interpretation 2.0 and approved visual baselines remain frozen.

## Release governance

Always update and verify Russian, Kazakh, and English README, user instructions, developer architecture, status, roadmap, project plan, changelog, release notes, and documentation manifest. User archives exclude `.github/workflows` unless local runtime explicitly requires it.
