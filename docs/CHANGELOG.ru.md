# Журнал изменений GAS RATIO PRO

## v225.6 — Physical Golden Baseline & Print Center Acceptance

- Зафиксированы SVG/PNG/PDF golden-artifacts для A4/A3 portrait/landscape.
- Добавлен end-to-end Professional Print Center acceptance runner.
- Исправлен PDF `LayoutError` для mixed-orientation physical preview.
- Все 51 legacy regression contract классифицированы в machine-readable registry без silent `xfail`.
- Добавлен current-build identity contract и regeneration script.


## v225.4

- Видимый Professional Print Center рассчитывает точный физический пакет до экспорта.
- Добавлен выбор и просмотр каждой SVG-страницы, точный A4/A3-профиль, DPI и page count.
- DOCX/HTML получают канонический многостраничный preview без повторного layout и fallback на первую страницу.
- Page-aware package обновлён до v1.2, preview contract — до v1.1.
- Сводка, подписи и диагностика синхронизированы для русского, казахского и английского языков.

Полная история: [CHANGELOG.md](CHANGELOG.md).
