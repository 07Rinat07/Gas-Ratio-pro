

## External standards and dependency isolation

External file formats and third-party libraries are integrated only through project-owned adapters. Domain entities, Dataset Manifests, QC reports and Workbench contracts must remain independent from parser-specific objects. Heavy dependencies are loaded lazily. Source bytes are preserved before conversion, and every derived artifact records provenance. Adoption is governed by `OPEN_STANDARDS_POLICY.md`, `LICENSE_POLICY.md`, `RESEARCH_POLICY.md` and the machine-readable component registry.
# GAS RATIO PRO — Active Architecture

Status: Active  
Baseline: v200

Этот файл является единственным активным обзором архитектуры. Детальные спецификации подсистем остаются справочными и не определяют порядок реализации.

## Runtime chain

```text
run_app.ps1
→ app/streamlit_app.py::main
→ _run_modern_workbench
→ app.workbench_renderer.render_streamlit_workbench
→ WorkbenchController / Command Registry
→ Workbench UI layout contract
→ native Streamlit regions
```

## Workbench regions

```text
Command toolbar
Project Explorer | Workspace Host | Properties
Status Bar
```

## Dependency rule

```text
UI / Streamlit adapter
→ application controllers and renderer contracts
→ domain/application services
→ repositories/importers/exporters
```

Обратная зависимость запрещена. UI не выполняет инженерные расчёты, не читает репозитории напрямую и не хранит raw DataFrame.

## Runtime identity

Каждый production build показывает:

- номер build;
- абсолютный runtime source path;
- активный workspace.

Launcher не запускает новый сервер поверх занятого порта. Старый процесс текущего проекта перезапускается только с явным `-ForceRestart`.

## Production acceptance boundary

Автоматические тесты недостаточны для закрытия UI-этапа. Обязательны:

1. запуск через `run_app.ps1 -ForceRestart`;
2. визуальная проверка build и source path;
3. проверка пяти областей Workbench;
4. выполнение command-backed действий без traceback;
5. подтверждение LAS Viewer внутри Workspace Host.

## Workbench functional integration boundary (v202)

The Modern Workbench owns navigation, layout and command dispatch. Existing production Streamlit workflows remain the implementation of LAS import/analysis, LAS editing, LAS correlation, interpretation plots, printable reports, project exports and documentation. They are embedded through `render_modern_workbench_workspace()` and are not reimplemented in the renderer. This preserves one domain implementation while retiring the parallel legacy navigation shell.
