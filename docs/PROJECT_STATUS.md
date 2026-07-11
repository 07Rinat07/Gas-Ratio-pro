# GAS RATIO PRO — Current Project Status

Baseline: v193  
Current stage: Petrophysical Engine (next after completed Workbench production-entry correction)  
Last fully verified baseline: v193 — Modern Workbench is the default production Streamlit entry point; the previous UI is retained only behind the explicit `GAS_RATIO_PRO_LEGACY_UI` process environment flag; session state cannot activate legacy mode; Workbench renderer, command dispatch and responsive/accessibility contracts remain active; preflight OK.

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

- Petrophysical Engine formulas, units and calculation contracts remain the next Stage 4 increment after the completed v193 Workbench production-entry correction.

## 3. Следующий разрешённый инкремент

**Establish confirmed petrophysical formulas, units and transparent calculation contracts.**

Состав:

1. audit existing formula sources and implementation coverage;
2. define explicit input/output unit contracts;
3. expose calculation provenance and quality flags;
4. reject unsupported or dimensionally invalid inputs before calculation;
5. unit, integration and regression tests.

Modern Workbench Stage 3 окончательно завершён в v193 после подключения production entry point.

Stage 5 Modeling Engine в следующий инкремент не входит.
