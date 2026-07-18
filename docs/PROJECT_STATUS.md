# Текущее состояние — v225.10 Stable

Обновлено: 18 июля 2026 года.

## Активный этап

**Stage 5.1 — Field Calibration & Report Authorization Integration завершён.** Производственные формулы не изменялись.

## Field Calibration

- 10 методов используют project-owned synthetic field-surrogate dataset;
- registry и dataset содержат ownership/legal clearance, units, acceptance thresholds и fingerprints;
- gate рассчитывает RMSE, MAE, bias, max error, sensitivity и uncertainty envelopes;
- field-calibration gate: **10/10 passed**;
- final-report calibrated/authorized: **9/10**;
- evidence: `artifacts/validation/petrophysical_calibration_v225_10.json`.

## Report Authorization

- numerical validation, calibration и report policy объединены application service;
- method IDs переносятся через machine-readable DataFrame context;
- export authorization выполняется до PresentationModel и renderer;
- authorization IDs и gate IDs сохраняются в artifact и export history;
- Professional Print Center показывает read-only diagnostics на ru/kk/en;
- foundation Dual Water остаётся `blocked_final_report`.

## Стабильные контракты

Live Workbench Acceptance, full-frame A3 landscape layout, architecture boundaries, controlled visual baselines и Open Standards and Legal Research Governance остаются обязательными. Pixler rehabilitation, Ternary rehabilitation, Depth engineering panel и Reservoir Intelligence / Interpretation 2.0 не изменяются без evidence.

Итоговая проверка v225.10: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.

## Stabilization & Release Audit

Stable v225.8 Live Workbench Acceptance remains mandatory and currently passes **14/14** checks. Architecture boundaries, controlled visual baselines, full-frame report layout, and all numerical/calibration/authorization gates remain blocking.

## Следующий этап

**Stage 5.2 — Operator Dataset Import & Calibration Comparison.** Разрешены импорт operator-owned calibration packages, проверка data rights, project-scoped comparison и versioned authorization packages. Изменение формул без validation/calibration evidence запрещено.
