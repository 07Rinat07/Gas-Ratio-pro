# Next Step

Completed in v37: Workspace Session Manager for Modern UI.

The application can now capture, save, load and restore a lightweight workspace session: active project, well, LAS, workspace, selected intervals, active report, active plot, recent exports and window layout.

Next recommended increment: Modern Workspace shell foundation — Project Explorer, central workspace area, toolbar/status boundary and integration points for session restore/reset/export actions.

## PDF Preview foundation

- Added bounded raster preview generation for already-rendered PDF artifacts.
- The service prefers PyMuPDF and falls back to local `pdftoppm`.
- Preview rendering is limited to 1–12 pages and 72–180 DPI.
- Temporary source and page files are isolated outside project `data/` and removed automatically.
- Next step: connect the service to the Report Designer UI and cache previews by report signature.


## PDF Preview UI integration

- Connected bounded PDF page thumbnails to the Professional Export panel.
- Preview is generated only on explicit request after a matching PDF artifact exists.
- Thumbnails are cached by the actual PDF bytes, export request signature, page limit and DPI.
- Cache is invalidated when a new export artifact is completed or export settings are reset.
- The UI keeps download available when no local rasterizer is installed.
- Next step: add an optional compact two-column thumbnail layout and preview performance metrics.

## PDF Preview compact layout and metrics

- Added optional one-column and compact two-column thumbnail layouts.
- Added measured render duration, source PDF size, total thumbnail size and average thumbnail size.
- Layout selection does not invalidate the raster cache because it changes presentation only.
- Next step: add selective page-range preview and explicit preview-cache cleanup.

## Selective PDF page-range preview and cache cleanup

- Added selection of the first page for a bounded preview range.
- Included the starting page in the preview cache signature to prevent stale page sets.
- Added explicit cleanup of the current project's in-memory PDF thumbnail cache.
- Preserved actual page numbers for both PyMuPDF and `pdftoppm` backends.
- Next step: add previous/next page navigation and optional bounded DPI selection.

## PDF Preview navigation and bounded DPI

- Added previous/next navigation that moves by the selected bounded page group.
- Added optional raster quality control with fixed safe values: 72, 90, 110, 144 and 180 DPI.
- DPI participates in the preview cache signature, so quality changes cannot reuse stale thumbnails.
- Navigation clamps to the first and last valid page group when the exact PDF page count is known.
- Next step: add direct page-jump validation feedback and an optional lightweight preview prefetch for the adjacent page group.

## PDF Preview direct page-jump validation

- Added renderer-neutral validation for direct page jumps.
- Page numbers below 1 and beyond the known document end are normalized safely.
- The UI now explains when a requested page was adjusted and uses the normalized page consistently for cache signatures, rendering and navigation.
- Next step: add optional adjacent-range prefetch without increasing default rendering cost.

## Исправление runtime-сбоя панели экспорта

- Диапазон печати теперь вычисляется до формирования сигнатуры предпросмотра.
- Устранён `UnboundLocalError` для `print_top` и `print_bottom`.
- Виджеты Report Designer больше не задают одновременно значение через Session State и параметр `index`/`value`/`default`.
- Добавлены регрессионные тесты порядка вычислений и наличия кнопки отправки формы.

## Исправление снимка состояния Workbench с runtime-объектами

- Диспетчер Workbench больше не выполняет единый `deepcopy()` всего Session State.
- Значения состояния копируются по одному; неподлежащее копированию runtime-состояние сохраняется по ссылке.
- Навигация не падает, если в Session State присутствует `BackgroundExportManager` с `ThreadPoolExecutor` и `queue.SimpleQueue`.
- Для обычных словарей и списков сохранён глубокий rollback при ошибке команды.
- Добавлены регрессионные тесты успешной навигации и отката при наличии непиклируемой очереди.

## Изоляция runtime-сервисов Workbench

- Добавлен `RuntimeServiceRegistry` для process-local объектов, которые нельзя сериализовать или копировать.
- `BackgroundExportManager`, `DataframeRuntimeCache`, `PlotCache` и `RuntimeDiagnostics` больше не хранятся как обычные ключи состояния приложения.
- Rollback Workbench глубоко копирует обычные данные, но сохраняет идентичность отдельного runtime-реестра.
- Добавлена сериализуемая диагностика типов зарегистрированных сервисов без раскрытия самих объектов.
- Следующий шаг: постепенно перевести оставшиеся live-сервисы на тот же runtime-контейнер и добавить lifecycle shutdown при завершении сессии.

## Lifecycle shutdown для runtime-сервисов

- `RuntimeServiceRegistry` теперь выполняет best-effort shutdown всех зарегистрированных process-local сервисов.
- Поддерживаются сервисы с методами `close()` и `shutdown(wait=False)`; отсутствие lifecycle-метода считается корректным no-op.
- Ошибка закрытия одного сервиса не блокирует завершение остальных и возвращается как сериализуемый диагностический результат.
- `WorkbenchLifecycleManager.close_workspace()` освобождает runtime-сервисы и очищает registry текущей сессии.
- Следующий шаг: добавить явный shutdown при полном завершении Streamlit-сессии и телеметрию неуспешного закрытия сервисов.

## Телеметрия завершения runtime-сервисов

- Закрытие Workspace публикует сериализуемое событие `workbench.runtime_services.shutdown`.
- Сводка содержит общее число сервисов, число успешных закрытий, no-op сервисов и ошибок.
- Ошибки включают только ключ, тип, метод и текст исключения; live-объекты в историю событий не попадают.
- После полного shutdown контейнер runtime-реестра удаляется из application state, а следующий запрос создаёт новый чистый registry.
- Закрытие Workspace остаётся best-effort: сбой одного сервиса не блокирует остальные, но отражается в сообщении lifecycle-результата.
- Следующий шаг: подключить этот же boundary к подтверждённому завершению Streamlit-сессии, когда будет доступен стабильный session-dispose hook.

## PDF Preview: bounded adjacent-range prefetch

- Added an opt-in control for preloading exactly one next bounded page group.
- Preview Session State now uses a backward-compatible cache that keeps at most three recent ranges.
- Navigating into a prefetched range reuses its existing PNG thumbnails without another rasterization.
- Legacy single-entry preview cache payloads remain readable after the update.
- Prefetch never runs by default and remains constrained by the selected page limit and DPI.
- Next step: add lightweight cache-hit/prefetch telemetry and acceptance testing on a large multi-page report.

## PDF Preview cache and prefetch telemetry

- Added renderer-neutral cache lookup diagnostics (`hit`, source and bounded entry index).
- Streamlit now logs cache hit/miss events without exposing PDF or PNG payloads.
- Prefetch telemetry includes page range, render duration, thumbnail bytes and backend.
- Reusing an already-prefetched range emits a dedicated cache-hit event.
- Added an acceptance-style regression using a generated 24-page PDF and bounded 5-page windows.
- Next step: expose an optional compact in-UI preview cache statistic and evaluate memory pressure with several large reports.

## PDF Preview cache statistics and memory pressure

- Added an optional in-UI cache statistics panel for the current project session.
- The summary reports cached ranges, rendered pages, aggregate PNG bytes and the largest cached range.
- Renderer-neutral diagnostics classify memory pressure as `empty`, `ok`, `warning` or `critical` without copying PDF/PNG payloads.
- Warning and critical guidance recommends cache cleanup or lower DPI/page limits.
- Next step: add cache eviction telemetry and an optional per-project memory budget control.

## PDF Preview cache memory budget and eviction telemetry

- Added a per-project Session State memory budget selector for PDF preview thumbnails: 8, 16, 24 or 48 MiB.
- Cache insertion now evicts the oldest preview ranges until both the entry-count limit and memory budget are satisfied.
- The newest explicitly requested range is always retained, even if that single range exceeds the selected budget.
- Evictions emit payload-free telemetry with evicted count, released bytes, retained bytes and configured budget.
- Existing `store_pdf_preview_cache()` remains backward compatible and delegates to the new diagnostic storage API.
- Next step: return to the core interpretation workflow and implement project-persistent editable interval annotations.

## 2026-07-14: interpretation repository foundation completed

Completed the serializable `Project -> Well -> Interpretation -> Intervals` repository with UUID-based CRUD and atomic persistence. The next bounded increment is an application service/command layer that records reversible create/update/delete operations for undo/redo before Streamlit UI integration.

## Interpretation interval Undo/Redo command service

- Added `InterpretationIntervalCommandService` with bounded create/update/delete history.
- Undo/Redo restores complete serializable snapshots and refuses unsafe restoration after external repository changes.
- History is scoped to project, well and interpretation and contains no runtime objects.
- Interval loading now preserves both `created_at` and `updated_at`.
- Next step: connect the service to a focused Streamlit interval manager panel with create/edit/delete and Undo/Redo controls.

## Interpretation interval manager completed

- Added a unified manager for list/get/create/update/delete and Undo/Redo operations.
- Added overlap diagnostics with adjacent boundaries treated as non-overlapping.
- Strict overlap rejection is opt-in to preserve backward compatibility.
- Next step: connect the manager to a focused Streamlit interval panel with selection, create/edit/delete and Undo/Redo controls.

## Interpretation interval property service completed

- Added backend preparation for a focused interval properties panel.
- Partial edits preserve omitted values and ignore UI-only keys.
- All changes reuse repository validation and remain Undo/Redo-aware.
- Next step: connect the service to a focused Streamlit panel with interval selection and edit controls.

## Current next step

Manual interpretation intervals are now editable in the Streamlit interpretation workspace. The next increment should render these intervals as colored overlays on the tablet and synchronize selection between the panel and visualization.

### Completed: manual interval visualization

Manual interpretation intervals are now rendered on interpretation depth tracks and the engineering tablet. The next increment should add interval export (JSON/CSV/Excel) or improve direct chart selection, while preserving the current repository and command-service boundaries.

## Interpretation interval export

Completed: manual interpretation intervals can be downloaded from the interval panel as JSON, CSV or Excel. Exports include UUID, bounds, derived thickness/middle depth, type, color, comment, source and timestamps.

Next recommended increment: improve tablet interaction for manual intervals with direct selection/hover synchronization and configurable overlay visibility.

## Interpretation interval import

- JSON, CSV and Excel exports can now be imported back into the active interpretation.
- Supported modes are append-only, UUID upsert and complete replacement.
- A complete import is persisted atomically through the interval repository and recorded as one reversible command.
- Invalid schemas, missing columns and duplicate UUID values are rejected before persistence.
- Next step: synchronize selection and hover state between the interval table/panel and tablet overlays.

## Manual interval navigator

- Added a compact Plotly depth navigator for manually managed interpretation intervals.
- Clicking an interval marker synchronizes its UUID with the existing properties-panel selection state.
- Hover shows bounds, thickness, type and comment without exposing repository objects to Session State.
- Older Streamlit builds fall back to a non-interactive navigator instead of failing the workspace.
- Next step: add configurable overlay visibility/opacity or extend direct selection to the main tablet tracks.

## Manual interval overlay controls

- Added a presentation-only visibility toggle for manual interpretation intervals.
- Added bounded overlay opacity control from 0.04 to 0.55.
- Overlay settings do not modify repository interval data or command history.
- Selected interval synchronization remains available when overlays are hidden.
- Next step: add direct selection from the main tablet tracks or persist display preferences per project.

## Project-persistent manual interval display settings

- Manual interval overlay visibility and opacity are now stored per project and well.
- Display preferences use a small versioned JSON file next to the interpretation interval repository.
- Widget keys are scoped by project and well, preventing settings from leaking between active wells.
- Persistence is atomic and does not modify interval data or Undo/Redo history.
- Next step: add direct interval selection from the main tablet tracks.

## Direct manual interval selection on depth tracks

- Manual intervals can now be selected directly from the main interpretation depth charts.
- Selection stores only the interval UUID and synchronizes with the existing properties panel and tablet focus.
- Older Streamlit versions continue rendering charts without interactive selection.
- Next step: add direct selection to the engineering tablet interval track or add interval type management.

## Project-scoped interpretation interval type catalog

- Manual interval types are now managed through a project-scoped persistent catalog.
- Each type has a stable ID, display name, default color and description.
- Create and edit forms use catalog values while preserving legacy/custom interval types.
- Next step: add batch operations for manual intervals or direct selection on the engineering tablet track.

## Safe deletion for interpretation interval types

- The project type catalog now reports usage across all wells and interpretations.
- Types referenced by persisted intervals cannot be deleted accidentally.
- The Streamlit catalog shows interval, well and interpretation usage counts and disables unsafe deletion.
- Next step: add an explicit batch reassignment workflow for replacing a type across project intervals.

## Массовое переназначение типов интервалов

- Используемый тип можно переназначить на другой тип во всех скважинах и интерпретациях проекта.
- При переназначении можно применить цвет целевого типа или сохранить индивидуальные цвета интервалов.
- После успешного переназначения исходный тип безопасно удаляется из справочника.
- При ошибке пакетной операции уже изменённые файлы интервалов восстанавливаются.
- Следующий шаг: добавить предварительный просмотр затрагиваемых интервалов перед массовым переназначением.

## Предварительный просмотр переназначения типов интервалов

- Перед массовым переназначением показывается точный список затрагиваемых интервалов.
- Предварительный просмотр содержит скважину, интерпретацию, подпись, границы, мощность и текущий цвет.
- Формирование preview не изменяет файлы интервалов и справочник типов.
- Следующий шаг: добавить подтверждение операции с защитой от изменения данных между preview и применением.

## Подтверждение переназначения типов с защитой от устаревшего preview

- Массовое переназначение требует явного подтверждения пользователя.
- Preview содержит контрольный токен, рассчитанный по справочнику типов и файлам интервалов проекта.
- Если данные изменились между preview и применением, операция отклоняется без частичного изменения файлов и без удаления исходного типа.
- Следующий шаг: добавить журнал пакетных операций типов или отдельный механизм отмены проектного переназначения.

## Журнал пакетных операций типов интервалов

- Успешное проектное переназначение с удалением исходного типа записывается в отдельный версионированный журнал.
- Запись содержит дату, исходный и целевой типы, количество интервалов, скважин и интерпретаций, а также признак применения цвета.
- Журнал ограничен 200 последними операциями и отображается в интерфейсе справочника типов.
- Следующий шаг: добавить отдельный безопасный механизм отмены последнего проектного переназначения.

## Отмена последнего проектного переназначения типов

- Последнее массовое переназначение с удалением исходного типа можно безопасно отменить.
- Перед операцией сохраняется ограниченная резервная копия только затронутого справочника и файлов интервалов.
- Отмена проверяет контрольные суммы состояния после операции и блокируется, если данные были изменены позднее.
- После успешного восстановления запись журнала помечается как отменённая и повторная отмена запрещается.
- Следующий шаг: добавить экспорт журнала пакетных операций или перейти к групповым операциям над выбранными интервалами.

## Экспорт журнала пакетных операций типов

- Журнал проектных переназначений типов можно выгрузить в JSON, CSV и Excel.
- Экспорт содержит идентификатор операции, исходный и целевой типы, статистику, даты и статус отмены.
- JSON использует версионированную схему, а Excel содержит отдельный лист метаданных проекта.
- Экспорт не изменяет журнал, резервные копии или состояние интервалов.
- Следующий шаг: перейти к групповым операциям над выбранными ручными интервалами.


## Фильтрация журнала операций типов интервалов

- Журнал пакетных операций фильтруется по статусу и идентификаторам типов.
- Поиск выполняется до ограничения количества строк и не скрывает более старые совпадения.
- Исправлено безопасное отображение пустого журнала.
- Отмена всегда относится к фактически последней операции проекта, а не к первой строке фильтра.
- Следующий шаг: добавить постраничную навигацию или детальную карточку операции с её UUID и параметрами.

## Постраничная навигация и карточка операции журнала типов

- Журнал пакетных операций поддерживает постраничную загрузку после применения фильтров.
- Поиск учитывает UUID операции, исходный и целевой типы.
- Для выбранной записи отображается детальная карточка с полным UUID, статусом, датами и статистикой.
- Экспорт формируется для текущей отфильтрованной страницы; отмена по-прежнему применяется только к последней фактической операции проекта.
- Следующий шаг: добавить групповые операции над выбранными ручными интервалами или отдельный экспорт полного отфильтрованного журнала.

## Групповые операции над ручными интервалами

- Несколько интервалов можно выбрать и массово переназначить на другой тип.
- Цвет целевого типа можно применить ко всей группе или сохранить индивидуальные цвета.
- Выбранные интервалы можно удалить одной подтверждаемой операцией.
- Каждое групповое изменение сохраняется как один шаг Undo/Redo.
- Следующий шаг: добавить массовое редактирование комментария/источника либо перейти к прямому выбору интервалов на инженерном планшете.

## Массовое редактирование комментария и источника

- Для выбранных ручных интервалов можно массово заменить источник.
- Комментарий можно полностью заменить, очистить или добавить к существующему тексту.
- Изменение валидируется общей моделью интервала и сохраняется как один шаг Undo/Redo.
- Следующий шаг: добавить предварительный просмотр групповых изменений либо прямой выбор интервалов на инженерном планшете.

## Предварительный просмотр групповых операций интервалов

- Перед массовым изменением типа и цвета показываются текущие и целевые значения.
- Для комментария и источника отображается результат замены или добавления до сохранения.
- Предварительный просмотр удаления показывает точное количество затрагиваемых интервалов.
- Preview использует общую валидацию модели, не изменяет репозиторий и не создаёт шаг Undo/Redo.
- Следующий шаг: добавить защиту групповых операций от изменения выбранных интервалов между preview и применением.

## Batch interval workflow

- Групповые изменения типа, цвета, комментария, источника и удаление выполняются через подтверждённый preview.
- Preview содержит SHA-256 токен состояния выбранных интервалов и параметров операции.
- Устаревший preview блокируется до записи данных.
- Подтверждённые операции сохраняются в ограниченном сериализуемом журнале Session State.
- Каждая пакетная операция остаётся одним шагом Undo/Redo.


## Поиск, фильтрация и аналитика ручных интервалов

- Добавлен единый фильтр по тексту, типам, источникам, диапазону глубин и мощности.
- Отфильтрованный набор используется для выбора интервалов и групповых операций.
- Добавлена аналитика по количеству, типам, суммарной мощности и фактически покрытой глубине без двойного учёта пересечений.
- Текущая выборка экспортируется в JSON, CSV и Excel.
- Следующий крупный этап: контроль качества интерпретации, выявление конфликтов и формирование сводного отчёта по скважине.

## Сохранённые представления фильтров интервалов

- Пользователь может сохранить текущий набор фильтров под понятным названием.
- Представления изолированы по проекту, скважине и интерпретации.
- Применение представления восстанавливает поиск, типы, источники, диапазон глубин и ограничения мощности.
- Представления можно экспортировать и импортировать через версионированный JSON.
- Следующий крупный этап: контроль качества интерпретации, выявление конфликтов и сводный отчёт по скважине.


## Управление версиями интерпретации скважины

- Добавлен каталог интерпретаций уровня `Project → Well → Interpretation` с именем, описанием и стабильным ID.
- Пользователь может создавать пустые интерпретации, переключаться между ними и редактировать метаданные.
- Дублирование переносит интервалы, настройки отображения и сохранённые представления через staging-каталог с обновлением scope-метаданных.
- Удаление перемещает интерпретацию в локальную корзину скважины; доступно восстановление, а удаление последней интерпретации запрещено.
- Следующий крупный этап: контроль качества интерпретаций и сравнение нескольких версий одной скважины.

## Сравнение и перенос интервалов между версиями интерпретации

- Активную интерпретацию можно сравнить с другой версией той же скважины по стабильным UUID интервалов.
- Отображаются добавленные, удалённые, изменённые и неизменённые интервалы, включая список изменённых полей.
- Выбранные интервалы можно перенести из сравниваемой версии в активную с политикой конфликтов: заменить, пропустить или создать копию.
- Перенос защищён контрольным токеном preview, может запрещать пересечения и сохраняется одним шагом Undo/Redo.
- Следующий крупный этап: контроль качества версии интерпретации, выявление конфликтов и формирование сводного отчёта по скважине.

## Completed: interpretation three-way merge
- Base/source/target workspace merge is available from the interval panel.
- Merge preview reports automatic changes, conflicts, unchanged intervals and deletions.
- Confirmation tokens prevent applying a stale merge preview.
- The complete merge is persisted as one reversible interval command.

## Completed: interpretation revision history

Implemented named snapshots, revision comparison, stale-safe restore, deletion and retention cleanup for manual interpretation workspaces.

## Recommended next major stage

Add review/approval workflow for interpretation versions: draft/reviewed/approved statuses, validation gates, reviewer notes and release-ready export metadata.


## Interpretation approval and publication workflow

- Added persistent statuses: draft, in review, approved and published.
- Approved and published interpretations are read-only for interval mutations until reopened.
- Publication is bound to an existing revision and rejected when the revision no longer matches current interpretation content.
- Workflow transitions keep a bounded JSON-compatible audit history with comments and published revision UUID.
- Revision snapshots and interpretation duplication exclude workflow metadata, so approval state never contaminates content hashes or copied workspaces.
- Next step: add role-aware reviewers/signatures or begin the multi-well correlation workspace.

## Completed: role-aware publication workflow

- Interpretation publication transitions now enforce author, reviewer, publisher and administrator permissions.
- Every workflow event records actor ID, display name and role.
- The Streamlit workflow panel exposes the active local actor and role and displays them in the audit history.
- Audit history can be exported as JSON, CSV or Excel.
- The role model is serializable and independent from a future authentication provider.

## Recommended next major stage

Begin the multi-well correlation workspace using published interpretation revisions as immutable correlation inputs.
