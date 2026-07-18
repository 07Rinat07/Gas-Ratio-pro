# Field Calibration and Report Authorization Architecture

## Layers

1. `core/petrophysical_method_executor.py` — single entry point for production formulas.
2. `core/petrophysical_calibration_contract.py` — registry/dataset/gate/authorization schemas, data rights, and fingerprints.
3. `services/petrophysical_calibration_application_service.py` — RMSE/MAE/bias, sensitivity, and uncertainty envelopes.
4. `services/petrophysical_report_authorization_application_service.py` — composition of the numerical gate, calibration gate, and report policy.
5. `core/petrophysical_report_context.py` — method-ID propagation through `DataFrame.attrs`.
6. `reports/export_controller.py` and `services/presentation_export_runtime_application_service.py` — blocking export-boundary check.
7. `services/petrophysical_validation_diagnostics.py` — localised read-only view model.

## Invariants

- UI and renderers never decide whether a method is authorised.
- Authorization runs before presentation-model or artifact construction.
- Missing method context is an error when final-report authorization is required.
- A calibration dataset must carry machine-readable ownership/legal clearance.
- Formula execution is not duplicated inside the gate; the shared production executor is used.
- Foundation Dual Water remains `blocked_final_report` even when numerical and calibration gates pass.
- Authorization ID, gate IDs, and method IDs are persisted in export artifacts and history.

## Contracts

- `gas-ratio-pro/petrophysical-field-calibration-registry/v1`
- `gas-ratio-pro/petrophysical-field-calibration-dataset/v1`
- `gas-ratio-pro/petrophysical-field-calibration-gate/v1`
- `gas-ratio-pro/petrophysical-report-authorization/v1`
- `gas-ratio-pro/petrophysical-method-context/v1`

## Next stage

Stage 5.2 may add operator-owned calibration-package import and project-scoped comparisons only through data-rights validation. Formula changes without new validation/calibration evidence remain prohibited.
