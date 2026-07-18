# Page-aware басып шығару, шекаралар және visual regression архитектурасы

Revision: 6 · GAS RATIO PRO v225.8 stable

## Page-aware pipeline

`VisualizationScenePipeline` → `VisualizationPageAwarePackageBuilder` → `VisualizationCrossFormatParityGate` SVG/PNG/PDF/DOCX/HTML геометриясының жалғыз көзі болып қалады. `export_ready` тек жарамды пакет пен сәтті parity gate кезінде true болады.

## Түзетілген architecture boundaries

- destructive filesystem операцияларын Streamlit UI емес, `TemporaryFileApplicationService`/`DeleteEngine` орындайды;
- `ApplicationServiceContainer` бір session-scoped `CacheMetricsRegistry` иеленеді;
- correlation artifacts application service арқылы жасалады;
- route lifecycle, startup diagnostics және project cache coherence `RuntimeDiagnosticsApplicationService` ішінде;
- тікелей `st.rerun()` тек бірыңғай refresh gate ішінде рұқсат;
- UI infrastructure object жасамайды және raw DataFrame downstream жібермейді.

## Print readability

`reports.print_readability_contract.REPORT_PRINT_READABILITY` — PDF/DOCX ортақ контракты. Ол легенда қарпінің ең аз өлшемін, raster dimensions және `one-item-per-row` layout-ты бекітеді. Тесттер source мәтінін емес, public contract пен renderer мінез-құлқын тексереді.

## Controlled visual rebaseline

`config/visual_rebaseline_contracts_v225_7.json` 13 бекітілген semantic contract және әр canonical JSON snapshot үшін SHA-256 сақтайды. `VisualRebaselineRegistryService` тіркелмеген өзгерісті қабылдамайды. Бастапқы nodeid сақталды.

## Legacy remediation

`config/legacy_regression_contracts_v225_7.json` мұраланған 51 contract-тың бәрін бақылайды. v225.7-де 51 contract `status=resolved`, `resolved_in=v225.7` және evidence мәніне ие. Silent `xfail`, nodeid жою және review-сыз hash өзгертуге тыйым салынады.

## Build identity

`BUILD_VERSION` файлы Python runtime және PowerShell launcher үшін жалғыз нұсқа көзі. `core.build_info` оны импорт кезінде оқиды; `DEPLOYMENT_BUILD.txt` сол нұсқаны қамтуы тиіс.
