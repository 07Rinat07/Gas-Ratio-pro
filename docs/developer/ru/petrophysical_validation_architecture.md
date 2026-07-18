# Архитектура Petrophysical Engine Validation

Stage 5 разделяет production formulas, machine-readable method registry, synthetic reference datasets и application-service gate. UI и отчётные renderer-ы не имеют права изменять формулы или обходить gate.

## Layers

- `config/petrophysical_method_registry_v225_9.json` — provenance, units, applicability, report policy и tolerance.
- `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json` — синтетические input/expected cases.
- `core/petrophysical_validation_contract.py` — schema, fingerprint, structural/unit validation и manifest rows.
- `services/petrophysical_validation_application_service.py` — исполнение production functions, numerical comparison и final-report authorization.
- `scripts/run_petrophysical_validation_gate.py` — CLI и evidence writer.

## Gate semantics

Gate считается пройденным только при отсутствии structural errors и совпадении всех значений в пределах abs/relative tolerance. `authorize_methods(..., final_report=True)` дополнительно запрещает методы с `blocked_final_report`.
