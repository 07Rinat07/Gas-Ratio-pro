# Текущее состояние — v225.7

Обновлено: 18 июля 2026 года.

## Активный этап

**Stage 4 — Workbench UI Completion / Stabilization & Release Audit.** Сборка имеет статус **release candidate v225.7**.

## Реализовано

- устранены девять подтверждённых architecture-boundary нарушений без ослабления audit policy;
- удаление временных файлов перенесено в application lifecycle service и выполняется через `DeleteEngine`;
- cache telemetry создаётся контейнером один раз и передаётся сервисам через dependency boundary;
- route lifecycle, startup diagnostics и cache coherence принадлежат application service;
- прямой `st.rerun()` оставлен только внутри единого rerun gate;
- 26 brittle source assertions заменены исполняемыми behavior contracts (18 из legacy registry, Print Center contract и 7 PDF preview contracts);
- 13 визуальных legacy-проверок переведены на утверждённые semantic snapshots;
- добавлены `visual_rebaseline_contracts_v225_7.json` и SHA-256 validation;
- шесть исторических version pins заменены current-build identity contracts;
- пять устаревших Workbench compatibility assertions заменены runtime/view-model проверками;
- все 51 legacy regression contract имеют `resolved_in`, evidence и replacement contract;
- единым источником версии является корневой файл `BUILD_VERSION`;
- пользовательский архив не содержит `.github/workflows`.

## Legacy regression state

- зарегистрировано контрактов: **51**;
- закрыто в v225.7: **51**;
- активных legacy contracts: **0**;
- silent `xfail` и удаление тестов без replacement contract по-прежнему запрещены.

## Проверка релиза

- расширенный architecture/renderer/export/documentation контур: **480 passed**;
- полный regression suite: **2855 passed, 0 failed**;
- все 51 legacy nodeid входят в полный suite и проходят replacement contracts;
- новых regression failures v225.7: **0**;
- Python compileall: **passed**; 92 относительные Markdown-ссылки и 36 manifest-путей: **valid**.

Автоматический release gate пройден. Stable promotion остаётся заблокирован только до живой проверки Workbench.

## Следующий этап

Выполнить полный regression-аудит, запустить приложение через `run_app.ps1 -ForceRestart`, проверить пять областей Workbench и только после этого принять решение о переводе v225.7 из release candidate в stable.
