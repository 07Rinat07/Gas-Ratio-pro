# Field Calibration және Report Authorization архитектурасы

## Қабаттар

1. `core/petrophysical_method_executor.py` — production-формулаларды шақырудың бірыңғай нүктесі.
2. `core/petrophysical_calibration_contract.py` — registry/dataset/gate/authorization схемалары, data-rights және fingerprints.
3. `services/petrophysical_calibration_application_service.py` — RMSE/MAE/bias, sensitivity және uncertainty envelopes.
4. `services/petrophysical_report_authorization_application_service.py` — numerical gate, calibration gate және report policy біріктіруі.
5. `core/petrophysical_report_context.py` — method IDs мәндерін `DataFrame.attrs` арқылы тасымалдау.
6. `reports/export_controller.py` және `services/presentation_export_runtime_application_service.py` — export boundary-де блоктаушы тексеру.
7. `services/petrophysical_validation_diagnostics.py` — локализацияланған read-only view model.

## Инварианттар

- UI және renderer әдіске рұқсат беру туралы шешім қабылдамайды.
- Авторизация presentation model және artifact жасалмай тұрып орындалады.
- Міндетті авторизация кезінде method context болмауы қате болып саналады.
- Calibration dataset machine-readable ownership/legal clearance қамтуы тиіс.
- Gate ішінде formula execution қайталанбайды: ортақ production executor пайдаланылады.
- Foundation Dual Water numerical/calibration gates өткеннің өзінде `blocked_final_report` болып қалады.
- Authorization ID, gate IDs және method IDs export artifact/history ішінде жазылады.

## Контракттар

- `gas-ratio-pro/petrophysical-field-calibration-registry/v1`
- `gas-ratio-pro/petrophysical-field-calibration-dataset/v1`
- `gas-ratio-pro/petrophysical-field-calibration-gate/v1`
- `gas-ratio-pro/petrophysical-report-authorization/v1`
- `gas-ratio-pro/petrophysical-method-context/v1`

## Келесі кезең

Stage 5.2 operator-owned calibration packages импортын және project-scoped comparison мүмкіндігін тек data-rights validation арқылы қоса алады. Жаңа validation/calibration evidence жоқ формула өзгерісі тыйым салынған.
