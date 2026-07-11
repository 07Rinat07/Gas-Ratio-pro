# Visualization Layout Engine v78

## Назначение

Layout Engine отделяет расчет геометрии от renderer. Scene описывает инженерные
объекты, Layout Engine рассчитывает размеры и координаты, а SVG/PDF/UI renderer
только рисует готовую модель.

## Pipeline

`Source -> Domain Model -> Scene -> Layout -> Validation -> Renderer`

## Реализовано

- renderer-neutral `VisualizationLayout`;
- детерминированные bounds для canvas, content и tracks;
- отдельные header, axis и plot regions;
- единый depth mapping для всех tracks;
- проверка пустой сцены и некорректного depth domain;
- SVG renderer использует layout из pipeline и сохраняет fallback для plain scene.

## Следующий шаг

Добавить Axis and Grid Model: ticks, major/minor grid, curve scale labels и
renderer-neutral axis formatting.
