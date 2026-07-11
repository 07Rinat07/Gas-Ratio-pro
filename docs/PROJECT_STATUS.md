# GAS RATIO PRO — Current Project Status

Baseline: v180  
Current stage: LAS Viewer completion  
Last fully verified baseline: v179 — 1743 tests passed; preflight OK. Visualization Engine Stage 1 is complete. LAS-open workflow completed in v180.

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

**Build the complete multi-track viewer from imported LAS curves.**

Состав:

1. использовать payload, созданный LAS-open workflow;
2. построить полный multi-track viewer из доступных LAS curves;
3. сохранить renderer-neutral track/layout contracts;
4. корректно обработать пустые и полностью null curves;
5. покрыть построение unit, integration и regression tests.

LAS-open workflow подтверждён: importer → project storage → visualization payload → compact viewer session. Raw dataframe в UI session state не сохраняется.

Никакие audit/bookmark/licensing функции в следующий инкремент не входят.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
