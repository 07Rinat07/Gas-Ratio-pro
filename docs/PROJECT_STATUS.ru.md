# Текущее состояние — v225.11 Stable

Обновлено: 18 июля 2026 года.

## Активный этап

**Stage 5.2 — Operator Dataset Import & Calibration Comparison завершён.** Production formulas не изменялись.

## Operator calibration packages

- ZIP содержит только `manifest.json`, `calibration_registry.json` и `calibration_dataset.json`;
- импорт разрешён только для `operator_owned`, `licensed` или `public_domain` данных;
- project scope, owner, legal basis, processing/derivative permissions и expiration являются блокирующими;
- package, file и rights fingerprints проверяются при импорте и каждом использовании;
- `package_id + version` immutable, конфликтующая версия отклоняется;
- private operator data хранятся только в `data/projects/<project>/petrophysics/operator_calibration` и не попадают в релизный архив.

## Calibration comparison

- project baseline можно сравнивать с operator package;
- поддерживается сравнение двух импортированных versions;
- по каждому методу фиксируются pass/fail, RMSE, max error, uncertainty width и deltas;
- comparison evidence имеет детерминированный `comparison_id`;
- comparison не изменяет формулы и не выбирает метод автоматически.

## Project report authorization

- активный operator package применяется до PresentationModel и renderer;
- методы, покрытые package, используют его calibration и data-rights;
- остальные методы используют утверждённый Stage 5.1 baseline;
- создаётся versioned project authorization package;
- artifact и export history schema v5 содержат authorization package ID и operator fingerprint;
- смена authorization/rights context очищает project export cache;
- foundation Dual Water остаётся `blocked_final_report`.

## Evidence

- `artifacts/validation/petrophysical_operator_calibration_v225_11.json`;
- Stage 5.2 gate: импорт 1/1, comparison 10/10, project authorization 9/9;
- итоговая проверка: **2915 passed, 0 failed**;
- Live Workbench Acceptance: **14/14**.

## Стабильные контракты

Stable v225.8 Live Workbench Acceptance, full-frame A3 landscape layout, architecture boundaries, controlled visual baselines, numerical validation, field calibration и authorization до renderer остаются обязательными.

Reservoir Intelligence / Interpretation 2.0, Pixler rehabilitation, Ternary rehabilitation и Depth engineering panel не изменяются без explicit validation evidence.

## Stabilization & Release Audit

Package import не может обходить Stage 5/5.1 gates. Private data не распространяются. `.github/workflows` не включается в пользовательский архив.

## Следующий этап

**Stage 5.3 — Calibration Package Trust & Review Workflow.** Возможные работы: detached signatures, trust registry, reviewer approval, package revocation и controlled promotion между проектами. Изменение production formulas без нового validation/calibration evidence запрещено.
