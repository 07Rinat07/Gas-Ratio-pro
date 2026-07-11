# GAS RATIO PRO — Current Project Status

Baseline: v183  
Current stage: LAS Viewer completion  
Last fully verified baseline: v183 — LAS Viewer track order, width, linear/log scale and visibility are integrated through one renderer-neutral configuration controller; preflight OK. Visualization Engine Stage 1 is complete.

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

**Implement LAS Viewer zoom, pan, fit and reset with stable large-LAS behavior.**

Состав:

1. использовать существующий shared viewport и command controller;
2. добавить renderer-neutral zoom, pan, fit и reset application workflow;
3. не дублировать вычисления viewport в UI;
4. подтвердить cache/downsampling compatibility на больших LAS;
5. покрыть unit, integration, performance и regression tests.

Track configuration подтверждён: один controller синхронизирует session/layout visibility, порядок и ширину tracks, а linear/log scale с диапазоном сохраняется в сериализуемом state и применяется к track/curve render contract.

Export и Stage 3 Workbench в следующий инкремент не входят.

## 4. Критерий перехода к LAS Viewer

Переход разрешён, когда:

- reference scenes проходят validation без fatal findings;
- SVG/PDF parity подтверждён;
- Unicode и печатные размеры проверены;
- large-LAS performance regression проходит;
- full tests и preflight зелёные.
