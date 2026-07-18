# Полевая калибровка и авторизация финального отчёта

## Назначение

Stage 5.1 добавляет второй обязательный уровень контроля поверх численного validation gate. Численно воспроизводимый метод допускается в финальный инженерный отчёт только после проверки полевого калибровочного контракта и report policy.

## Полевой калибровочный набор

В v225.10 используется **принадлежащий проекту синтетический field-surrogate dataset** (`project-owned`). Он не содержит сторонних скважинных данных, разрешён к распространению вместе с проектом и служит воспроизводимым acceptance-набором. Для каждого метода заданы входы, параметры, эталонный результат, единицы, допуски и распределения параметров.

## Диагностика в Professional Print Center

В read-only панели отображаются:

- численный статус метода;
- статус field calibration;
- report policy;
- RMSE и максимальная ошибка;
- ширина uncertainty envelope;
- итоговое разрешение или блокировка финального отчёта;
- идентификаторы validation, calibration и authorization gate.

Панель доступна на русском, казахском и английском языках и не изменяет исходные данные или формулы.

## Авторизация экспорта

Если расчётный DataFrame содержит machine-readable method context, финальный PDF/DOCX/HTML/bundle экспорт выполняется только после `PetrophysicalReportAuthorizationApplicationService.assert_authorized()`.

Проверка происходит **до построения PresentationModel и до запуска renderer**. При блокировке файл не создаётся, export history не выдаёт ложный успешный результат, а пользователь получает причину отказа.

## Ограничение foundation Dual Water

`petrophysics.sw_dual_water_foundation` проходит численную и диагностическую калибровку, но имеет policy `blocked_final_report`. Его нельзя включить в финальный инженерный отчёт как полноценную промышленную модель Dual Water.

## Воспроизводимая проверка

```bash
python scripts/run_petrophysical_stage_5_1_gate.py
```

Evidence сохраняется в `artifacts/validation/` и содержит fingerprints контрактов, calibration gate, authorization ID и method-level решения.
