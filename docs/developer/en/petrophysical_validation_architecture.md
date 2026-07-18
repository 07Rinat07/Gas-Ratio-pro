# Petrophysical Engine Validation architecture

Stage 5 separates production formulas, the machine-readable method registry, synthetic reference datasets, and the application-service gate. UI and report renderers may not change formulas or bypass the gate.

## Layers

- `config/petrophysical_method_registry_v225_9.json` — provenance, units, applicability, report policy, and tolerance.
- `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json` — synthetic input/expected cases.
- `core/petrophysical_validation_contract.py` — schemas, fingerprinting, structural/unit validation, and manifest rows.
- `services/petrophysical_validation_application_service.py` — production-function execution, numerical comparison, and final-report authorization.
- `scripts/run_petrophysical_validation_gate.py` — CLI and evidence writer.

## Gate semantics

The gate passes only when there are no structural errors and every value matches within the absolute/relative tolerance. `authorize_methods(..., final_report=True)` additionally rejects `blocked_final_report` methods.
