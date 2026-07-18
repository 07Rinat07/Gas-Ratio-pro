# Текущее состояние — v225.6

Обновлено: 18 июля 2026 года.

## Активный этап

**Stage 4 — Acceptance, Visual Baseline & Legacy Contract Audit / Stabilization & Release Audit.** Сборка имеет статус **release candidate v225.6**.

## Реализовано

- зафиксированы визуальные golden-artifacts для A4/A3 в книжной и альбомной ориентации;
- manifest проверяет SVG, PNG и PDF, физические размеры, пагинацию, track partition, page chrome и SHA-256;
- добавлен воспроизводимый скрипт `scripts/regenerate_physical_golden_artifacts.py`;
- реализован end-to-end `ProfessionalPrintCenterAcceptanceRunner`;
- acceptance-path охватывает сохранение и выбор пользовательского профиля, visible preview, parity gate, HTML/PDF/DOCX bundle и SVG/PNG static delivery;
- исправлен `LayoutError` при встраивании портретного physical preview в альбомный PDF-отчёт;
- все 51 legacy regression contract внесены в machine-readable audit registry;
- legacy-аудит запрещает silent `xfail` и удаление теста без replacement contract;
- пользовательский архив не содержит `.github/workflows`.

## Проверка релиза

- целевой v225.6 acceptance/golden/audit и совместимый renderer/export набор: **150 passed**;
- полный regression suite: **2853 tests, 2802 passed, 51 failed**;
- 51 failure относятся к унаследованному registry и остаются видимыми;
- новых regression failures v225.6: **0**;
- Python compileall, документационные ссылки, manifest и архив: **успешно**.

## Следующий этап

Закрыть 9 подтверждённых architecture-boundary debts и заменить brittle source/visual assertions утверждёнными behavior/golden contracts. Перевод в stable допускается только после нулевого release-blocking debt.
