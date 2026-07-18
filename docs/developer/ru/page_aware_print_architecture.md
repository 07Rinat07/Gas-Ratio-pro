# Архитектура page-aware печати, границ и visual regression

Revision: 5 · GAS RATIO PRO v225.7

## Page-aware pipeline

`VisualizationScenePipeline` → `VisualizationPageAwarePackageBuilder` → `VisualizationCrossFormatParityGate` остаётся единственным источником SVG/PNG/PDF/DOCX/HTML геометрии. `export_ready` требует валидного пакета и успешного parity gate.

## Исправленные architecture boundaries

- destructive filesystem operations выполняет `TemporaryFileApplicationService`/`DeleteEngine`, а не Streamlit UI;
- `ApplicationServiceContainer` владеет единственным session-scoped `CacheMetricsRegistry`;
- correlation artifacts создаются через application service;
- route lifecycle, startup diagnostics и project cache coherence принадлежат `RuntimeDiagnosticsApplicationService`;
- прямой `st.rerun()` допускается только внутри единого refresh gate;
- UI не создаёт инфраструктурные объекты и не передаёт raw DataFrame downstream.

## Print readability

`reports.print_readability_contract.REPORT_PRINT_READABILITY` является общим контрактом PDF/DOCX. Он фиксирует минимальные шрифты легенды, raster dimensions и `one-item-per-row` layout. Тесты проверяют публичный контракт и фактическое поведение renderer-ов, а не текст исходных файлов.

## Controlled visual rebaseline

`config/visual_rebaseline_contracts_v225_7.json` содержит 13 утверждённых semantic contracts и SHA-256 каждого канонического JSON-снимка. `VisualRebaselineRegistryService` отклоняет незарегистрированное или неутверждённое изменение. Исходные nodeid сохранены.

## Legacy remediation

`config/legacy_regression_contracts_v225_7.json` отслеживает все 51 унаследованный contract. В v225.7 все 51 имеют `status=resolved`, `resolved_in=v225.7` и evidence. Silent `xfail`, удаление nodeid и изменение hash без review запрещены.

## Build identity

Файл `BUILD_VERSION` — единый источник версии для Python runtime и PowerShell launcher. `core.build_info` читает его при импорте; `DEPLOYMENT_BUILD.txt` должен содержать ту же версию.
