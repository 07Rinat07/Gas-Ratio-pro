# GAS RATIO PRO — Active Architecture

Status: Active  
Baseline: v225.7

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

Обратная зависимость запрещена. UI не выполняет инженерные расчёты, не читает repositories напрямую, не уничтожает infrastructure artifacts и не создаёт session-scoped telemetry dependencies.

## Application boundary remediation — v225.7

- temporary-file destruction принадлежит `TemporaryFileApplicationService` и выполняется через `DeleteEngine`;
- cache metrics registry создаётся `ApplicationServiceContainer` один раз на session scope;
- correlation artifacts передаются через application service, а не конструируются UI-слоем;
- route lifecycle, startup diagnostics и cache coherence принадлежат runtime diagnostics application service;
- UI запрашивает rerun только через единый rerun gate;
- UI contracts описывают поведение navigation, launcher, documentation, search и export surfaces без source-code assertions.

## Visual contract boundary

Visual acceptance проверяет semantic snapshot, а не случайные количества Plotly traces или строки исходного кода. Утверждённые snapshots находятся в `config/visual_rebaseline_contracts_v225_7.json`, имеют канонический SHA-256 и изменяются только через controlled rebaseline review.

## Print and report readability

PDF и DOCX используют общий `reports/print_readability_contract.py` для минимальной типографики, размеров preview и layout легенды. Renderer-specific значения не должны дублироваться в UI или тестах.

## Runtime identity

Корневой `BUILD_VERSION` является единственным источником версии. `core.build_info`, `DEPLOYMENT_BUILD.txt`, launcher badge и release metadata обязаны совпадать.

Каждый production build показывает:

- номер build;
- абсолютный runtime source path;
- активный workspace.

Launcher не запускает новый сервер поверх занятого порта. Старый процесс текущего проекта перезапускается только с явным `-ForceRestart`.

## External standards and dependency isolation

External file formats and third-party libraries are integrated only through project-owned adapters. Domain entities, Dataset Manifests, QC reports and Workbench contracts remain independent from parser-specific objects. Heavy dependencies are loaded lazily. Source bytes are preserved before conversion, and every derived artifact records provenance. Adoption is governed by `OPEN_STANDARDS_POLICY.md`, `LICENSE_POLICY.md`, `RESEARCH_POLICY.md` and the machine-readable component registry.

## Production acceptance boundary

Автоматические тесты недостаточны для stable promotion UI-этапа. Обязательны:

1. запуск через `run_app.ps1 -ForceRestart`;
2. визуальная проверка build и source path;
3. проверка пяти областей Workbench;
4. выполнение command-backed действий без traceback;
5. подтверждение LAS Viewer внутри Workspace Host.
