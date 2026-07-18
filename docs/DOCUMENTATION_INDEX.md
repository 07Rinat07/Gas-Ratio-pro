# GAS RATIO PRO — Documentation Index

## Единственный активный управляющий комплект

1. [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) — последовательность и Definition of Done.
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — фактический статус и один следующий разрешённый шаг.
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — активная архитектурная схема и runtime boundary.
4. [`DOCUMENTATION_INDEX.md`](DOCUMENTATION_INDEX.md) — эта карта документации.
5. [`16_Acceptance/LIVE_WORKBENCH_ACCEPTANCE_V225_8.ru.md`](16_Acceptance/LIVE_WORKBENCH_ACCEPTANCE_V225_8.ru.md) — stable-promotion evidence.

История изменений хранится в [`CHANGELOG.md`](CHANGELOG.md), но changelog не является планом или статусом.

## Справочные документы

Каталоги `00_...`–`16_...`, пользовательские руководства и спецификации подсистем являются справочными. Они не могут переопределять активный roadmap или status.

## Архив

Исторические roadmap, progress, sprint и version-note документы находятся в `docs/archive/`. Они не участвуют в выборе следующей задачи.

## Правило обновления

После инкремента:

- всегда обновляется `PROJECT_STATUS.md`;
- `PROJECT_ROADMAP.md` обновляется только при изменении этапа или Definition of Done;
- `ARCHITECTURE.md` обновляется только при изменении активной архитектуры;
- `CHANGELOG.md` получает запись о версии;
- новые `NEXT_STEP`, `PROGRESS`, `ROADMAP_vN` и `STATUS_vN` файлы запрещены.
