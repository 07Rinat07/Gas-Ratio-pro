# План реализации v225.7

## Цель

Устранить девять architecture-boundary violations, заменить brittle source assertions исполняемыми behavior tests и выполнить controlled visual rebaseline без скрытия регрессий.

## Выполненные работы

1. Lifecycle и инфраструктурное удаление перенесены из UI в application service.
2. Session-scoped cache telemetry передана application container.
3. Route/startup/cache-coherence lifecycle закреплён за runtime diagnostics service.
4. Rerun разрешён только через единый gate.
5. 26 source assertions заменены behavior/view-model contracts (18 legacy, Print Center contract и 7 PDF preview contracts).
6. 13 визуальных контрактов переведены на semantic snapshot manifest с SHA-256.
7. Historical version pins заменены current-build identity contracts.
8. Все 51 legacy contract закрыты с evidence и replacement test.

## Definition of Done

- 9 из 9 architecture tests проходят;
- 26 из 26 source-contract replacements проходят;
- 13 из 13 visual snapshots валидны;
- active legacy debt равен нулю;
- полный regression suite: **2855 passed, 0 failed**;
- расширенный release-контур: **480 passed**;
- документация `ru/kk/en` синхронизирована.
