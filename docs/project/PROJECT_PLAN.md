# План проекта Gas Ratio Pro

Обновлено: 18 июля 2026 года. Активная сборка: `v225.6`.

## Завершённый этап — v225.6

- четыре physical golden baselines A4/A3 portrait/landscape;
- reproducible golden regeneration и checksum verification;
- полный Professional Print Center acceptance-path;
- auto-scale raster preview по фактическому PDF frame;
- machine-readable audit всех 51 legacy regressions;
- replacement policy без silent `xfail`;
- трёхъязычная документация и release governance.

## Следующий разрешённый инкремент — Legacy Contract Remediation

1. Исправить architecture-boundary нарушения, не ослабляя audit policy.
2. Перенести brittle source assertions на view-model и runtime behavior.
3. Согласовать visual rebaseline через golden artifacts.
4. Удалять obsolete tests только после добавления replacement tests.
5. Повторить full regression и stable promotion gate.

## Definition of Done

- все четыре golden profile manifest проходят без изменения checksum;
- E2E acceptance создаёт валидные HTML/PDF/DOCX и SVG/PNG;
- каждый legacy contract имеет решение и replacement;
- release-blocking architecture debt равен нулю;
- версия, инструкции, status, roadmap, changelog и manifest синхронизированы на `ru/kk/en`.
