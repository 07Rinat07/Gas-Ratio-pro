# План проекта Gas Ratio Pro

Обновлено: 18 июля 2026 года. Активная сборка: `v225.8 stable`.

## Завершённый инкремент — Stable Promotion & Live Workbench Acceptance

- добавлен кроссплатформенный acceptance runner;
- временный Streamlit server проходит health gate;
- официальный AppTest исполняет реальную Workbench-сессию;
- подтверждены build version, stable channel, абсолютный source path и entry-point SHA-256;
- проверены Toolbar, Project Explorer, Workspace Host, Properties и Status Bar;
- LAS command и LAS Workspace проходят без traceback;
- итог: **14/14 acceptance checks passed**;
- Windows launcher поддерживает `run_app.ps1 -Acceptance`;
- документация и инструкции синхронизированы на русском, казахском и английском.

## Следующий разрешённый инкремент — Petrophysical Engine Validation Foundation

1. Зафиксировать текущий Method Registry и список формул.
2. Связать каждый method ID с источником, лицензией, единицами и applicability domain.
3. Подготовить reference datasets и expected results.
4. Определить numerical tolerance и uncertainty metadata.
5. Реализовать application-service validation gate и regression tests.
6. Не изменять Interpretation 2.0 и visual baseline без отдельного утверждённого evidence.

## Definition of Done

- build channel остаётся `stable`;
- live acceptance воспроизводится локально и проходит 14/14;
- каждый петрофизический метод имеет machine-readable provenance;
- validation datasets не содержат непроверенных или нелегально полученных данных;
- вычислительный результат воспроизводим в пределах утверждённого tolerance;
- README, instructions, status, roadmap, changelog, release notes и manifest синхронизированы на `ru/kk/en`.
