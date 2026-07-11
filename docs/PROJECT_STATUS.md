# GAS RATIO PRO — Current Project Status

Baseline: v196  
Current stage: Workbench UI Completion  
Last fully verified runtime baseline: v193 — Modern Workbench is the default production Streamlit entry point. Implementation baseline v196 completes the interactive application-level providers and command-backed panes inside the five-region engineering layout. The confirmed plan inserts the confirmed Workbench UI Completion stage before Petrophysical Engine so the shell is completed as an engineering workspace before additional domain modules are integrated.

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

- Toolbar actions, project-tree hydration, selection-driven Properties, embedded LAS visualization and supported dock resizing are implemented.
- Final real desktop/mobile responsive, keyboard and production workflow smoke verification remains before Stage 4 can close.
- Petrophysical Engine work is intentionally deferred until Workbench UI Completion passes its Definition of Done.

## 3. Следующий разрешённый инкремент

**Final Stage 4 responsive/accessibility and production workflow verification.**

Состав:

1. verify the interactive five-region layout on supported phone/tablet/laptop/wide profiles;
2. verify keyboard focus order for toolbar, project tree, workspace actions and dock lifecycle;
3. production smoke for project entry, LAS activation, navigation, dock collapse/restore/resize and export action exposure;
4. fix only confirmed presentation/integration defects;
5. full Workbench/LAS Viewer regression and preflight.

Stage 4 remains active until these final verification items pass.
Stage 5 Petrophysical Engine and Stage 6 Modeling Engine remain outside the next increment.
