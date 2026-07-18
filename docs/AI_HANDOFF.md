# Latest implementation — Field Calibration & Report Authorization v225.10

## Release state

- Build: `v225.10`.
- Channel: `stable`.
- Stage 5.1 implementation is complete.
- Numerical validation: **10/10 passed**.
- Field calibration: **10/10 passed**.
- Final-report authorised: **9/10**.
- Foundation Dual Water: `blocked_final_report`.
- Full regression: **2896/2896 passed**.
- Live Workbench Acceptance: **14/14 passed**.

## Architecture

- `core/petrophysical_method_executor.py` is the shared production execution boundary.
- `config/petrophysical_field_calibration_registry_v225_10.json` defines calibration policy and data rights.
- `data/validation/petrophysics/petrophysical_field_calibration_cases_v225_10.json` is a project-owned synthetic field surrogate.
- `services/petrophysical_calibration_application_service.py` computes error metrics, sensitivity, and uncertainty envelopes.
- `services/petrophysical_report_authorization_application_service.py` combines validation, calibration, and report policy.
- `core/petrophysical_report_context.py` propagates method IDs into export.
- `services/presentation_export_runtime_application_service.py` authorises before model/renderer construction.
- `services/petrophysical_validation_diagnostics.py` provides the ru/kk/en read-only Print Center view.
- `scripts/run_petrophysical_stage_5_1_gate.py` writes machine-readable evidence.

## Critical policy

No formula change is permitted without updated provenance, units, reference validation, calibration evidence, uncertainty, and report policy. Operator datasets must be owned or legally cleared. Foundation Dual Water must not be relabelled as a full industrial implementation.

## Next authorised stage

Stage 5.2 — Operator Dataset Import & Calibration Comparison: data-rights validation, immutable package fingerprints, project-scoped comparisons, and versioned authorization packages.

## Release governance

Always update and verify Russian, Kazakh, and English README, user instructions, developer architecture, status, roadmap, project plan, changelog, release notes, and documentation manifest. User archives exclude `.github/workflows` unless local runtime explicitly requires it.
