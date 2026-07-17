# Текущее состояние — v225.1

Professional Print Center и Visualization Engine используют renderer-neutral модель отчёта и компактный snapshot schema-v2 с безопасной миграцией schema-v1 и защитой будущих схем.

Завершён физический page-aware инкремент печати:

- отдельные профили A4/A3 portrait/landscape;
- минимальный кегль 7.5–8 pt, минимальная линия 0.50–0.55 pt и минимальная физическая ширина трека 28–30 мм;
- автоматическое разбиение широких планшетов по трекам без изменения порядка, кривых и шкал;
- одинаковый page contract для PDF и SVG, PNG-страницы растеризуются из тех же SVG;
- HTML/PDF/DOCX отчёты встраивают все страницы планшета;
- asset registry и bundle-манифесты сохраняют все страницы и одну geometry signature;
- агрегированная QA сверяет полное покрытие примитивов и физическое число PDF/SVG-страниц.

Канонический план проекта: [`project/PROJECT_PLAN.md`](project/PROJECT_PLAN.md).

Следующий разрешённый инкремент: подключить page-aware asset registry к одношаговому Professional Print Center, добавить общий page chrome/легенду и убрать одностраничные fallback-пути только после parity-проверки.
