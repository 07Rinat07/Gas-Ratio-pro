# GAS RATIO PRO — Current Project Status

Baseline: v185  
Current stage: LAS Viewer completion  
Last fully verified baseline: v185 — current LAS Viewer viewport exports to SVG/PDF through the existing Visualization Engine pipeline with strict validation blocking and geometry parity; preflight OK. Visualization Engine Stage 1 is complete.

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

**Handle LAS Viewer errors, empty curves, null intervals and invalid units.**

Состав:

1. нормализовать и классифицировать viewer-level ошибки входных curves;
2. исключать пустые и полностью null curves без нарушения track layout;
3. корректно обрабатывать null intervals и частично отсутствующие значения;
4. валидировать и диагностировать invalid/unsupported units;
5. покрыть unit, integration, export и regression tests.

Экспорт текущего вида подтверждён: application service использует уже вычисленный current viewport pipeline, не пересчитывает layout в UI, делегирует strict validation SVG/PDF renderers и подтверждает общий geometry signature через Export QA.

Stage 3 Workbench в следующий инкремент не входит.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
