# Petrophysical Engine Validation архитектурасы

Stage 5 production formulas, machine-readable method registry, synthetic reference datasets және application-service gate қабаттарын бөледі. UI және есеп renderer-лері формулаларды өзгерте немесе gate-ті айналып өте алмайды.

## Layers

- `config/petrophysical_method_registry_v225_9.json` — provenance, units, applicability, report policy және tolerance.
- `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json` — synthetic input/expected cases.
- `core/petrophysical_validation_contract.py` — schema, fingerprint, structural/unit validation және manifest rows.
- `services/petrophysical_validation_application_service.py` — production functions орындау, numerical comparison және final-report authorization.
- `scripts/run_petrophysical_validation_gate.py` — CLI және evidence writer.

## Gate semantics

Gate structural errors болмаған және барлық мәндер abs/relative tolerance шегінде сәйкес болғанда ғана өтеді. `authorize_methods(..., final_report=True)` қосымша `blocked_final_report` әдістерін тоқтатады.
