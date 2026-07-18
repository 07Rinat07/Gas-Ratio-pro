# Текущее состояние — v225.8 Stable

Обновлено: 18 июля 2026 года.

## Активный этап

**Stage 4 — Workbench UI Completion завершён.** Сборка `v225.8` переведена в канал **stable** после автоматизированного Live Workbench Acceptance.

## Stable promotion

- реальный временный Streamlit server успешно отвечает на `/_stcore/health`;
- build badge, `BUILD_VERSION`, `BUILD_CHANNEL`, абсолютный runtime source path и entry point согласованы;
- Toolbar, Project Explorer, Workspace Host, Properties и Status Bar отрисовываются без traceback;
- command-backed действие LAS выбирает `nav.las_workspace`;
- LAS Viewer и действие открытия LAS Workspace выполняются без traceback;
- результат acceptance: **14/14 passed**;
- acceptance contract: `config/live_workbench_acceptance_contract_v225_8.json`;
- machine-readable evidence: `artifacts/acceptance/live_workbench_acceptance_v225_8.json`.

## Stabilization & Release Audit

Architecture boundaries, the 51 resolved legacy contracts, controlled visual semantic snapshots, and the live acceptance contract remain mandatory stable-release gates. Silent `xfail`, hidden failures, and test deletion without a replacement contract are prohibited.

## Regression state

- full v225.8 regression suite: **2858 passed, 0 failed**;
- acceptance и stable-promotion tests добавлены поверх baseline;
- architecture-boundary debt: **0**;
- активных legacy regression contracts: **0**;
- controlled visual semantic snapshots остаются обязательными.

## Следующий этап

**Stage 5 — Petrophysical Engine Validation Foundation.** Разрешены только method registry, provenance формул, эталонные datasets, численные допуски и application-service validation gate. Изменение утверждённых формул, Interpretation 2.0 или visual baseline без validation evidence запрещено.
