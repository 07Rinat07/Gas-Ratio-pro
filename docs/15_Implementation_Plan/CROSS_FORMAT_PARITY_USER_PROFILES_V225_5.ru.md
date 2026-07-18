# v225.5 — Cross-format parity gate, retirement legacy export и пользовательские профили

## Цель

Сделать физический page-aware package единственным источником Professional Print Center для SVG, PNG, PDF, DOCX и HTML, автоматически блокировать несовпадения форматов и добавить сохраняемые безопасные A4/A3-профили.

## Реализация

1. `VisualizationCrossFormatParityGate` сверяет page count, физические размеры, track partition, geometry signature и canonical preview pages.
2. `VisualizationPageAwarePackage` v1.3 требует успешный parity gate для `export_ready`.
3. `UserPhysicalPrintProfileStore` сохраняет пользовательские профили в JSON и восстанавливает их между сессиями.
4. Пользовательские параметры не могут ослаблять базовые minimum font/line/track floors.
5. Professional report и LAS Viewer используют `PageAwareStaticArtifact`.
6. Multi-page SVG/PNG выдаётся ZIP-пакетом с manifest; first-page fallback запрещён.
7. Legacy CompositeLog static-export удалён из рабочего пути.
8. UI и документация синхронизированы на `ru/kk/en`.

## Definition of Done

- parity gate блокирует повреждённый пакет;
- UI показывает parity status и gate id;
- A4/A3 пользовательский профиль сохраняется и применяется к layout;
- SVG/PNG не теряют страницы;
- тесты, build metadata и документация соответствуют v225.5.
