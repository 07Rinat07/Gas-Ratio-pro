# План проекта Gas Ratio Pro

Обновлено: 18 июля 2026 года. Активная сборка: `v225.7`.

## Завершённый этап — v225.7

- устранены 9 architecture-boundary violations;
- lifecycle, cache telemetry, route/startup/cache-coherence и rerun переданы правильным слоям;
- 26 source assertions заменены behavior contracts (18 legacy, Print Center contract и 7 PDF preview contracts);
- 13 visual contracts переведены на semantic snapshot manifest;
- obsolete version pins заменены current-build identity contracts;
- все 51 legacy contracts закрыты с evidence и replacement tests;
- `BUILD_VERSION` стал единым источником версии;
- документация и инструкции синхронизированы на русском, казахском и английском;
- полный regression suite завершён: **2855 passed, 0 failed**.

## Следующий разрешённый инкремент — Stable Promotion & Live Workbench Acceptance

1. Запустить приложение через `run_app.ps1 -ForceRestart`.
2. Подтвердить build и абсолютный runtime source path.
3. Проверить toolbar, Project Explorer, Workspace Host, Properties и Status Bar.
4. Проверить command-backed действия и LAS Viewer без traceback.
5. Перевести v225.7 в stable только при отсутствии release-blocking failures.

## Definition of Done

- все 51 legacy contracts имеют статус resolved;
- architecture-boundary active debt равен нулю;
- semantic visual snapshots проходят SHA-256 validation;
- полный suite не содержит новых failures;
- live Workbench acceptance подтверждён;
- версия, README, инструкции, status, roadmap, changelog, release notes и manifest синхронизированы на `ru/kk/en`.
