# GAS RATIO PRO — Current Project Status

Baseline: v181  
Current stage: LAS Viewer completion  
Last fully verified baseline: v181 — LAS-open workflow and complete multi-track viewer are verified; preflight OK. Visualization Engine Stage 1 is complete.

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

- Export blocking и structural regression реализованы; остаются точечные исправления только по подтверждённым визуальным дефектам.
- LAS Viewer foundation существует, но полный пользовательский open → view → interact → export workflow ещё не подтверждён как законченный продукт.
- Modern Workbench и новая главная страница не начинаются до завершения LAS Viewer.

## 3. Следующий разрешённый инкремент

**Integrate the shared depth viewport, cursor and selection across all LAS Viewer tracks.**

Состав:

1. использовать готовый multi-track viewer contract;
2. синхронизировать единый depth viewport для всех видимых tracks;
3. подключить общий cursor и selection без UI business logic;
4. сохранить renderer-neutral interaction contracts;
5. покрыть unit, integration и regression tests.

Multi-track viewer подтверждён: imported payload → curve filtering → deterministic tracks → compact viewer state → Visualization Render Model. Пустые и полностью null curves исключаются до render pipeline.

Никакие track configuration, export, audit/bookmark/licensing функции в следующий инкремент не входят.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
