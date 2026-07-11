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
