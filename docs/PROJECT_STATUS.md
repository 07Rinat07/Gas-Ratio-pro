# GAS RATIO PRO — Current Project Status

Baseline: v190  
Current stage: Modern Workbench and new main page  
Last fully verified baseline: v190 — LAS Viewer is integrated as the primary Workbench module with synchronized LAS context, navigation route, active tool and dock focus; renderer-facing zoom/pan/fit/reset, cursor, selection and SVG/PDF export actions use application services; preflight OK.

## 1. Что подтверждено кодом и тестами

Visualization Engine:

- Domain Model, Scene, Layout и Render Model;
- Axis/Grid, Track, Curve Quality, Label/Legend и Print Layout;
- SVG/PDF renderers и geometry signature parity;
- adaptive downsampling, cache и memory budget;
- viewport, pan/zoom, hit testing, cursor и selection;
- render/export QA и Render Validation Pipeline;
- strict export enforcement: SVG/PDF export блокируется при fatal/error geometry findings;
- три эталонные multi-track сцены для linear, Unicode и overlay regression;
- утверждённые SVG/PDF reference artifacts с SHA-256 manifest и structural regression checks.

LAS Viewer foundation:

- viewer session и track layout;
- viewport-aware render pipeline;
- synchronized cursor/selection overlays;
- workspace persistence/autosave foundations.

## 2. Что не считается завершённым

- Responsive и accessibility audit ещё не выполнены.

## 3. Следующий разрешённый инкремент

**Implement project and recent-session entry points without duplicating Workbench navigation.**

Состав:

1. единые project/recent-session entry contracts для существующего Workbench shell;
2. открытие проекта и восстановление последней сессии через Command Framework;
3. маршрутизация в существующие navigation routes без параллельного UI workflow;
4. отсутствие прямых repository/file operations в UI;
5. unit, integration и regression tests.

LAS Viewer primary-module integration завершена в v190.

Stage 4 Petrophysical Engine в следующий инкремент не входит.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
