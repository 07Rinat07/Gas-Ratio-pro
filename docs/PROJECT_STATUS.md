# Текущее состояние — v225.9 Stable

Обновлено: 18 июля 2026 года.

## Активный этап

**Stage 5 — Petrophysical Engine Validation Foundation завершён.** Формулы не изменялись; создан обязательный machine-readable validation gate.

## Validation foundation

- 10 методов зарегистрированы в `config/petrophysical_method_registry_v225_9.json`;
- 10 synthetic reference cases находятся в `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json`;
- каждый метод имеет provenance, units, applicability, limitations, absolute/relative tolerance и uncertainty metadata;
- application service выполняет реальные production-функции;
- gate: **10/10 passed**, final-report eligible: **9/10**;
- `petrophysics.sw_dual_water_foundation` численно воспроизводим, но имеет policy `blocked_final_report`;
- evidence: `artifacts/validation/petrophysical_validation_v225_9.json`.

## Адаптивный макет отчётов

- A3 landscape PDF использует фактическую ширину и высоту ReportLab frame;
- metadata, легенды, статистика и текстовые таблицы занимают полный рабочий frame;
- DOCX использует ширину текущей section, HTML — responsive 100% width;
- `print-readability/v1.1` и visual baseline v225.9 блокируют возврат к узкой левой колонке.

## Stabilization & Release Audit

Stage 4 Live Workbench Acceptance (**14/14 passed**), architecture boundaries, controlled visual semantic snapshots и закрытые legacy contracts остаются обязательными. Silent `xfail`, скрытие failures и изменение формулы без evidence запрещены.

Финальная проверка v225.9: **2881 passed, 0 failed**; расширенный report/export контур: **338 passed**; Live Workbench Acceptance: **14/14**; petrophysical validation: **10/10**.

## Следующий этап

**Stage 5.1 — Field Calibration & Report Authorization Integration.** Разрешены field-owned calibration datasets, parameter uncertainty/sensitivity, read-only diagnostics и подключение `authorize_methods(..., final_report=True)` к финальному export boundary.
