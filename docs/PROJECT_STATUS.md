# GAS RATIO PRO — Current Project Status

Baseline: v197  
Current stage: Petrophysical Engine  
Last fully verified runtime baseline: v197 — Modern Workbench is the default production Streamlit entry point and now renders with native Streamlit containers as a real five-region engineering workspace. The production command-result contract, toolbar actions, Project Explorer, workspace host, Properties and Status Bar are verified by runtime-oriented smoke tests.

## 1. Что подтверждено кодом и тестами

Visualization Engine:

- Domain Model, Scene, Layout и Render Model;
- Axis/Grid, Track, Curve Quality, Label/Legend и Print Layout;
- SVG/PDF renderers и geometry signature parity;
- adaptive downsampling, cache и memory budget;
- viewport, pan/zoom, hit testing, cursor и selection;
- render/export QA и strict Render Validation Pipeline.

LAS Viewer:

- real LAS-open workflow и multi-track construction;
- shared viewport, cursor and selection;
- track configuration and stable large-LAS navigation;
- current-view SVG/PDF export;
- curve/null/unit validation.

Modern Workbench:

- shell, navigation model and Dock Manager;
- atomic Command Framework/Event Bus dispatch;
- LAS Viewer primary-module lifecycle;
- project and recent-session entry points;
- four responsive viewport profiles: phone, tablet, laptop and wide;
- horizontal overflow guard and 44 px minimum interactive target;
- deterministic unique focus order and keyboard interaction semantics;
- accessible labels, roles, descriptions and landmarks in renderer contracts;
- WCAG 2.2 AA contrast/readability checks for active presentation tokens;
- presentation contracts remain serializable and contain no raw DataFrame or runtime service objects;
- Modern Workbench is now the real default application startup path;
- legacy UI cannot be selected through stale browser/session state and requires an explicit operational environment flag.

## 2. Что не считается завершённым

- Workbench UI Completion is complete.
- Petrophysical Engine formula/unit/provenance work remains active.
- Modeling Engine remains deferred until Petrophysical Engine Definition of Done.

## 3. Следующий разрешённый инкремент

**Petrophysical Engine contract audit and enforcement.**

Состав:

1. audit existing VSH, PHIE and Archie formula implementations against registered sources;
2. define explicit input/output unit contracts and canonical units;
3. add calculation provenance and quality flags;
4. block incompatible or dimensionally invalid inputs before output curves are written;
5. integrate through existing application services without domain calculations in UI;
6. targeted regression, full preflight and status update.

Stage 6 Modeling Engine remains outside the next increment.
