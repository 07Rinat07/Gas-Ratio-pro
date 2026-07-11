# GAS RATIO PRO — Current Project Status

Baseline: v194  
Current stage: Workbench UI Completion  
Last fully verified runtime baseline: v193 — Modern Workbench is the default production Streamlit entry point. Planning baseline v194 inserts the confirmed Workbench UI Completion stage before Petrophysical Engine so the shell is completed as an engineering workspace before additional domain modules are integrated.

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

- The production Workbench currently renders a minimal shell rather than a complete engineering workspace.
- Project Explorer, workspace host, contextual Properties panel, command toolbar and operational status bar are not yet integrated into the real screen layout.
- Petrophysical Engine work is intentionally deferred until Workbench UI Completion passes its Definition of Done.

## 3. Следующий разрешённый инкремент

**Complete the production Workbench engineering layout.**

Состав:

1. implement the full-screen Workbench layout and central workspace host;
2. connect command toolbar/ribbon to existing renderer actions and Command Framework;
3. render Project Explorer and context-sensitive Properties as docked application views;
4. add operational Status Bar from serializable Workbench context;
5. place LAS Viewer inside the workspace host without moving calculations into UI;
6. preserve responsive, keyboard and accessibility contracts;
7. unit, integration, smoke, regression and preflight tests.

Stage 3 remains completed: shell architecture and production entry are confirmed.
Stage 4 Workbench UI Completion is now active because the real production screen exposed an incomplete presentation layer.
Stage 5 Petrophysical Engine and Stage 6 Modeling Engine are outside the next increment.
