# План проекта Gas Ratio Pro

Обновлено: 18 июля 2026 года. Активная сборка: `v225.5`.

## Обязательные инженерные принципы

- один pipeline является источником физической геометрии;
- `export_ready` требует успешный cross-format parity gate;
- пользовательские A4/A3 профили не могут ослаблять readability floors;
- multi-page SVG/PNG не сокращается до первой страницы;
- документация и инструкции обновляются синхронно на `ru / kk / en`.

## Завершённый этап — v225.5

- parity gate SVG/PNG/PDF/DOCX/HTML;
- page-aware package v1.3;
- persistent user profiles;
- manifest-backed static bundles;
- retirement CompositeLog static-export;
- parity status в Professional Print Center;
- тесты и документация на трёх языках.

## Следующий разрешённый инкремент — Stage 4 Acceptance & Stable Promotion

1. Выполнить пользовательский acceptance-path создания и выбора профиля.
2. Проверить A4/A3 portrait/landscape и custom profiles на реальных данных.
3. Зафиксировать visual golden artifacts.
4. Разобрать remaining legacy test failures.
5. Выпустить stable только после полного release gate.

## Definition of Done

- package parity подтверждена автоматически;
- физический профиль видим и воспроизводим;
- все страницы сохраняются во всех форматах;
- legacy first-page/static fallback отсутствует;
- build metadata, README, инструкции, status, roadmap, changelog и manifest синхронизированы.
