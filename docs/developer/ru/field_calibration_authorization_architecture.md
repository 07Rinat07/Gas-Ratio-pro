# Архитектура Field Calibration и Report Authorization

## Слои

1. `core/petrophysical_method_executor.py` — единая точка вызова production-формул.
2. `core/petrophysical_calibration_contract.py` — схемы registry/dataset/gate/authorization, data-rights и fingerprints.
3. `services/petrophysical_calibration_application_service.py` — RMSE/MAE/bias, sensitivity и uncertainty envelopes.
4. `services/petrophysical_report_authorization_application_service.py` — объединение numerical gate, calibration gate и report policy.
5. `core/petrophysical_report_context.py` — перенос method IDs через `DataFrame.attrs`.
6. `reports/export_controller.py` и `services/presentation_export_runtime_application_service.py` — блокирующая проверка на export boundary.
7. `services/petrophysical_validation_diagnostics.py` — локализованный read-only view model.

## Инварианты

- UI и renderer не принимают решение о разрешении метода.
- Авторизация выполняется до создания presentation model и артефакта.
- Отсутствующий method context при обязательной авторизации является ошибкой.
- Calibration dataset обязан иметь machine-readable ownership/legal clearance.
- Formula execution не дублируется в gate: используется общий production executor.
- Foundation Dual Water остаётся `blocked_final_report`, даже если numerical/calibration gates пройдены.
- Authorization ID, gate IDs и method IDs записываются в export artifact/history.

## Контракты

- `gas-ratio-pro/petrophysical-field-calibration-registry/v1`
- `gas-ratio-pro/petrophysical-field-calibration-dataset/v1`
- `gas-ratio-pro/petrophysical-field-calibration-gate/v1`
- `gas-ratio-pro/petrophysical-report-authorization/v1`
- `gas-ratio-pro/petrophysical-method-context/v1`

## Следующий этап

Stage 5.2 может добавлять импорт operator-owned calibration packages и project-scoped comparison только через data-rights validation. Изменение формул без нового validation/calibration evidence запрещено.
