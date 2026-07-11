# GAS RATIO PRO — Current Project Status

Baseline: v195  
Current stage: Workbench UI Completion  
Last fully verified runtime baseline: v193 — Modern Workbench is the default production Streamlit entry point. Implementation baseline v195 establishes the full-screen five-region engineering layout. The confirmed plan inserts the confirmed Workbench UI Completion stage before Petrophysical Engine so the shell is completed as an engineering workspace before additional domain modules are integrated.

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

- The five-region production layout is now integrated, but toolbar commands, project-tree hydration, contextual selection properties and the embedded LAS visualization still require full interactive completion.
- Dock resizing must be completed within supported Streamlit boundaries and verified on real desktop/mobile runs.
- Petrophysical Engine work is intentionally deferred until Workbench UI Completion passes its Definition of Done.

## 3. Следующий разрешённый инкремент

**Complete interactive Workbench panes inside the v195 production layout.**

Состав:

1. connect toolbar groups to existing renderer actions and Command Framework;
2. hydrate Project Explorer from an application-level serializable project-tree provider;
3. bind Properties to the existing Workbench selection/context contracts;
4. embed the existing LAS Viewer render payload in the central workspace host;
5. finish supported dock sizing/collapse behavior and operational viewport/scale status;
6. preserve responsive, keyboard and accessibility contracts;
7. unit, integration, production smoke, regression and preflight tests.

Stage 3 remains completed: shell architecture and production entry are confirmed.
Stage 4 Workbench UI Completion is now active because the real production screen exposed an incomplete presentation layer.
Stage 5 Petrophysical Engine and Stage 6 Modeling Engine are outside the next increment.
