# Sprint 1 Integration Stabilization

## Цель

Довести текущую ветку Sprint 1 до рабочего состояния перед дальнейшим переходом к Workspace Framework.

## Выполнено

- Проверена компиляция проекта через `python -m compileall`.
- Восстановлена совместимость LAS Creation Wizard v2:
  - `LasCreationMode`;
  - `build_las_creation_wizard_preview_v2`;
  - `finalize_las_creation_wizard`;
  - `summarize_source_las`;
  - UI-ready rows for modes, templates, issues and steps.
- Добавлен fallback импорт Streamlit для не-UI тестового окружения, где пакет `streamlit` не установлен.
- Добавлен backward-compatible alias `delete_well(...)` для старых вызовов удаления скважины.
- Preflight dependency check переведен в warning для отсутствующих runtime packages в изолированной test-среде.

## Проверка

- `python -m compileall -q .` — OK.
- `tests/test_las_creation_wizard_v2.py` — OK.
- `tests/test_well_manager_service.py` — OK.
- `tests/test_well_repository.py` — OK.

## Оставшиеся ограничения

Часть UI snapshot/string tests относится к устаревшим текстам Dashboard и документации. Их нужно синхронизировать отдельным проходом после завершения фактического Project Manager refactoring.

## LAS Manager Service Integration Pass

Sprint 1 integration now routes project LAS operations through `services/las_manager_service.py`.

Covered operations:

- list project LAS versions;
- list project LAS well cards;
- save uploaded/prepared LAS files into project storage;
- archive and restore LAS versions;
- physically delete LAS versions;
- clear all LAS versions from a project;
- read LAS bytes/dataframes;
- export selected LAS versions as ZIP.

The Streamlit UI entry points for dashboard counters, recent activity, project workspace loader and project LAS file panel now call the service layer instead of directly calling low-level `projects.las_files` repository functions.

## Service Compatibility Pass 5 — ExportManagerService

Completed items:

- Export delete and clear operations are routed through `DeleteEngine`.
- Export resources, file handles, and cache entries are released before deletion.
- Project storage index is synchronized after export deletion/cleanup.
- Compatibility aliases were preserved for old UI integration: `list`, `count`, `read_bytes`, `delete`, `clear`, `refresh`.
- Service contract added: `docs/09_Architecture/contracts/EXPORT_MANAGER_SERVICE_CONTRACT.md`.
