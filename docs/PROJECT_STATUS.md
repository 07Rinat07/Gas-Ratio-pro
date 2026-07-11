# GAS RATIO PRO — Current Project Status

Baseline: v184  
Current stage: LAS Viewer completion  
Last fully verified baseline: v184 — LAS Viewer zoom, pan, fit and reset are integrated through one renderer-neutral navigation controller with large-LAS viewport filtering and cache compatibility; preflight OK. Visualization Engine Stage 1 is complete.

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

**Export the current LAS Viewer view to SVG/PDF through Visualization Engine.**

Состав:

1. использовать текущий shared viewport и общий Render Model;
2. экспортировать именно текущий вид без повторного вычисления layout в UI;
3. сохранить SVG/PDF geometry parity и validation blocking;
4. покрыть unit, integration, export и regression tests.

Zoom, pan, fit и reset подтверждены: один application controller использует существующие viewport commands, сохраняет общую глубинную область для всех tracks, ограничивает pan LAS-диапазоном и возвращает compact performance profile. Large-LAS regression подтверждает viewport filtering, bounded cache reuse и отсутствие raw dataframe в session state.

Stage 3 Workbench в следующий инкремент не входит.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
