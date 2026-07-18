# v225.10 — Field Calibration, Sensitivity & Report Authorization

## Цель

Добавить field-calibration evidence и блокирующую авторизацию финального отчёта без изменения производственных формул.

## Выполнено

1. создан project-owned synthetic field-surrogate dataset для 10 методов;
2. зафиксированы ownership/legal clearance, единицы и acceptance thresholds;
3. рассчитаны RMSE, MAE, bias и max error;
4. добавлены parameter sensitivity и uncertainty envelopes;
5. numerical validation и calibration объединены с report policy;
6. method context переносится из расчёта в экспорт;
7. authorization выполняется до model/renderer;
8. Professional Print Center показывает read-only diagnostics на ru/kk/en;
9. authorization evidence записывается в artifact и export history;
10. foundation Dual Water остаётся blocked для final report.

Итоговая проверка v225.10: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.
