# GAS RATIO PRO — отраслевой план развития данных и интеграций

Дата актуализации: 2026-07-16
Статус: утверждён как стратегическое направление; реализация поэтапная.

## 1. Целевой продукт

GAS RATIO PRO развивается из LAS-ориентированного инженерного приложения в единую subsurface-платформу, объединяющую скважинные данные, геофизику, геологические модели, GIS, результаты разработки и нормативную отчётность.

Ключевой архитектурный принцип: крупные отраслевые форматы не загружаются целиком в память и не связываются напрямую со Streamlit UI. Каждый формат подключается через application-service boundary, metadata catalog, chunked/streaming reader и проектное хранилище артефактов.

## 2. Приоритет форматов

### P0 — фундамент платформы

1. Реестр форматов и capabilities: расширение, MIME/type, importer, exporter, preview, validation, streaming support.
2. Единый Dataset Manifest: идентификатор, источник, CRS, единицы, диапазоны, размер, checksum, версия схемы и provenance.
3. Artifact Store: исходный файл хранится отдельно от индексируемых метаданных и производных preview.
4. SQL metadata catalog: проекты, скважины, datasets, curves, models, spatial layers, reports, revisions и lineage.
5. Chunked I/O, byte-budget, фоновые задачи и отмена для крупных данных.

### P1 — ближайшая прикладная ценность

- DLIS: цифровой каротаж, frame/channel inventory, units, depth/time indexing, выборочный импорт каналов.
- SEG-Y Revision 2.1: чтение textual/binary headers, trace headers, geometry/QC и decimated preview без полной загрузки traces.
- Shape/GeoPackage/GeoTIFF: GIS-слои, CRS validation/reprojection, карты скважин и контуров.
- HDF5/NetCDF: chunked datasets для больших научных массивов и производных данных.
- GRDECL: импорт/экспорт Eclipse-style grid/property keywords с validation report.

### P2 — обмен моделями и симуляторы

- RESQML 2.2 как основной открытый обменный стандарт для структурных, геологических и reservoir-моделей.
- GRDECL export profiles для Eclipse-совместимых workflow.
- Адаптеры tNavigator/CMG строятся как отдельные export profiles после фиксации реальных контрактов и тестовых наборов.
- Legacy RESCUE допускается как отдельный compatibility adapter, но не как основной внутренний формат.
- Прямые proprietary Petrel project readers не входят в ядро без официального SDK, лицензии и юридически допустимого контракта; интеграция выполняется через RESQML/GRDECL/SEG-Y и поддерживаемые vendor exports.

### P3 — визуализация и совместные workflow

- 3D scene service: trajectories, horizons, faults, grids, seismic slices и well intersections.
- Multi-resolution/level-of-detail rendering; UI получает только подготовленные tiles/decimated arrays.
- Correlation, seismic-well tie, formation tops и cross-domain interpretation.
- Simulation result ingestion, time steps, property maps и comparison dashboards.

## 3. База данных и хранение

Рекомендуемая модель:

- SQLite для локального single-user проекта и индекса метаданных;
- PostgreSQL/PostGIS для multi-user/server deployment и пространственных запросов;
- файловое/object storage для SEG-Y, DLIS, HDF5, NetCDF, GeoTIFF, RESQML packages и отчётов;
- HDF5/Zarr/NetCDF только для массивов, а не как замена транзакционному каталогу;
- checksum, immutable source artifact, derived artifact lineage и schema-versioned metadata.

NoSQL не вводится без конкретного запроса: для инженерных сущностей, версий и связей SQL/PostGIS предсказуемее и лучше обеспечивает целостность.

## 4. Отчётность и регуляторные профили

PDF/DOCX остаются форматами представления, но нормативные формы должны быть versioned templates:

- jurisdiction: KZ / RU / company;
- authority and document type;
- template version and effective date;
- обязательные разделы, таблицы, подписи и единицы;
- validation rules и audit manifest;
- воспроизводимый snapshot исходных данных и расчётов.

Регуляторные правила нельзя жёстко зашивать в расчётное ядро. Они обновляются независимо через template/rule packages и проходят отдельную юридико-методическую верификацию перед production use.

## 5. Безопасность и качество

Для каждого импортера обязательны:

- parser sandbox/ограничение ресурсов для недоверенных файлов;
- размерные лимиты, streaming и cancellation;
- validation report до сохранения в проект;
- units/CRS/depth-reference normalization;
- checksum и provenance;
- deterministic fixtures и golden-file tests;
- отсутствие тяжёлых payload в session state и diagnostics.

## 6. Последовательность реализации

1. Data Format Registry, Dataset Manifest, duplicate detection, immutable lineage и metadata-scanner protocol — реализовано.
2. Artifact Store — реализовано; далее SQLite metadata catalog schema.
3. DLIS metadata/channel inventory importer.
4. GIS foundation: CRS, GeoPackage/Shape/GeoTIFF metadata and map preview.
5. SEG-Y header/geometry/QC importer с decimated preview.
6. HDF5/NetCDF chunk store.
7. GRDECL parser/validator/export profile.
8. RESQML 2.2 package catalog and staged import.
9. 3D scene service и LOD pipeline.
10. Versioned regulatory report profiles KZ/RU после получения точных утверждённых форм и экспертной проверки.

## 7. Критерии готовности формата

Формат считается поддержанным только если есть:

- capability contract;
- parser/import application service;
- metadata-only scan;
- validation and actionable errors;
- bounded memory behavior;
- project persistence and lineage;
- preview/navigation integration;
- unit, malformed-file, large-file and round-trip tests;
- документация ограничений и совместимости.


## Legacy LAS compatibility (pre-2.0)

GAS RATIO PRO must support archival LAS files older than LAS 2.0, including LAS 1.x and field files that only partially follow the specification. Legacy support is a first-class compatibility requirement, not an optional conversion utility.

Principles:
- tolerant read, strict write;
- original files remain immutable;
- no silent unit, mnemonic or depth correction;
- every heuristic produces a stable warning code;
- users can review a compatibility report before normalization or export;
- strict modern validation remains available separately;
- Russian, Kazakh and English explanations are generated from the same language-neutral codes.

Planned diagnostics include old section aliases, absent `VERS`, legacy `WRAP`, unusual delimiters, DOS/legacy encodings, malformed parameter cards, missing `NULL`, non-monotonic depth and inconsistent curve counts.

### Archival LAS compatibility
Support LAS older than 2.0, legacy encodings (including Windows-1251), shortened sections, and non-standard data delimiters through bounded tolerant scanning. Preserve original bytes and expose stable machine-readable diagnostics.


## v222.30 — Legacy LAS UI and catalog operations
- Added manual SQLite metadata-catalog reconciliation in Workbench Diagnostics Center.
- Added bounded decimal-comma and fixed-width legacy LAS diagnostics.
- Added stable validation codes and synchronized ru/kk/en messages.
