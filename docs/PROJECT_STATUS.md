# GAS RATIO PRO — Current Project Status

Baseline: v187  
Current stage: Modern Workbench and new main page  
Last fully verified baseline: v187 — Modern Workbench shell now uses one application-level navigation model; every section activates one registered tool through the command framework, and LAS Workspace is connected to the existing LAS Viewer service payload without UI business logic; preflight OK.

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

- Dock Manager и полноценное управление панелями ещё не завершены.
- Command Framework и Event Bus требуют финальной интеграции на уровне Workbench shell.
- Responsive и accessibility audit ещё не выполнены.

## 3. Следующий разрешённый инкремент

**Build the Dock Manager and tool panels.**

Состав:

1. единый application-level Dock Manager;
2. открытие, закрытие, сворачивание и фокус панелей через command layer;
3. сохранение dock layout как presentation state;
4. подключение зарегистрированных Workbench tools к dock panes без бизнес-логики в UI;
5. unit, integration и regression tests.

Workbench shell и единый navigation model завершены в v187.

Stage 4 Petrophysical Engine в следующий инкремент не входит.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
