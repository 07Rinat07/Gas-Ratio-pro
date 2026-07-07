# Structural Modeling Specification Draft

## Назначение

Structural Modeling Workspace отвечает за базовый структурный каркас геологической модели GAS RATIO PRO.

## Объекты

- Structural Framework
- Horizon Group
- Structural Horizon
- Structural Fault
- Structural Zone
- Structural Layer
- Structural Surface

## Проверки

- наличие горизонтов;
- корректность ссылок зон на кровлю и подошву;
- отличие кровли от подошвы;
- корректность диапазонов глубин;
- наличие поверхностей, связанных с горизонтами и разломами;
- корректность связей разломов с горизонтами.

## Выходные данные

- manifest;
- Markdown report;
- UI-ready tables;
- registry JSON внутри проекта.
