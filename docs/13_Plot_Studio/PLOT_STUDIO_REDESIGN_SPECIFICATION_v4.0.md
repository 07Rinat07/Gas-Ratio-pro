# GAS RATIO PRO — PLOT STUDIO PROFESSIONAL REDESIGN SPECIFICATION v4.0

## 1. Проблема

Текущие графики интерпретации недостаточно информативны, плохо управляются пользователем и не соответствуют уровню профессионального инженерного ПО.

---

## 2. Обязательные функции

### 2.1 Manual Scale

Для каждой дорожки:

- X Min;
- X Max;
- Auto/Manual;
- Linear/Log;
- Reverse scale;
- Units.

Для глубины:

- Depth From;
- Depth To;
- Depth Step;
- Grid spacing.

### 2.2 Mouse Interaction

- mouse wheel zoom;
- drag pan;
- box zoom;
- double click reset;
- synchronized tracks;
- tooltip;
- crosshair.

### 2.3 Markers

- gas;
- oil;
- water;
- condensate;
- OWC;
- GOC;
- GWC;
- FWL;
- pay zones;
- core intervals;
- perforations;
- tests;
- comments.

### 2.4 Print / Export

- selected depth interval;
- full well;
- multi-page PDF;
- PNG;
- SVG;
- TIFF;
- JPEG.

---

## 3. Acceptance Criteria

Plot Studio считается исправленным только если пользователь может:

1. Ввести вручную диапазон глубин.
2. Ввести вручную X min/X max.
3. Приблизить график мышью.
4. Передвинуть график мышью.
5. Вывести маркеры флюидов и контактов.
6. Напечатать выбранный интервал в PDF.
7. Экспортировать график в PNG/SVG.

---

## 4. Plot Studio Core Backend

Реализован первый backend-слой Plot Studio 2.0: `projects/plot_studio_core.py`.

### 4.1 Назначение

Plot Studio Core не выполняет отрисовку графиков и не изменяет LAS-данные. Модуль формирует неизменяемую renderer-independent модель рабочего пространства, которую можно безопасно передавать в Streamlit UI, Plotly renderer, export engine и будущие обработчики mouse zoom/pan.

### 4.2 Основные модели

- `PlotDepthRange` — общий интервал глубины для всех треков.
- `PlotViewportState` — состояние viewport: интервал глубины, синхронизация, активный трек, zoom/pan placeholders.
- `PlotCrosshairState` — общий crosshair для синхронного курсора.
- `PlotLayerState` — видимость слоев: curves, grid, annotations, markers, crosshair.
- `PlotRenderCurve` — нормализованная кривая для renderer-а.
- `PlotRenderTrack` — нормализованный трек с шириной, процентом ширины и кривыми.
- `PlotWorkspace` — полная модель рабочего пространства Plot Studio.

### 4.3 Реализованные функции

- построение workspace из `PlotTemplate`;
- ручное задание `Depth From` / `Depth To`;
- проверка корректности интервала глубины;
- синхронизация интервала глубины между видимыми треками;
- формирование crosshair state с ограничением по текущему интервалу;
- формирование serializable manifest для UI/export/debug;
- формирование таблицы треков для Streamlit/sidebar diagnostics;
- сохранение неизменяемости исходного workspace при смене интервала глубины.

### 4.4 Инженерные ограничения

- оригинальный LAS не изменяется;
- Plot Studio Core работает только с metadata/template model;
- viewport и workspace возвращаются как новые immutable объекты;
- невидимые треки исключаются из renderer manifest;
- шаблон валидируется перед построением workspace;
- при отсутствии видимых треков возвращается issue, а не аварийное падение renderer-а.

### 4.5 Подготовка к следующим этапам

Модуль подготавливает основу для следующих функций Roadmap:

1. Mouse Zoom.
2. Drag Pan.
3. Box Zoom.
4. Manual X/Y Scale UI.
5. Shared Crosshair.
6. Professional Track Layout.
7. PDF/PNG/SVG/TIFF export pipeline.

---

## 5. Plot Studio Mouse Zoom & Navigation Backend

Реализован backend-слой интерактивной навигации Plot Studio 2.0: `projects/plot_studio_navigation.py`.

### 5.1 Назначение

Модуль принимает нормализованные события UI: колесо мыши, box zoom, pan, reset, undo и redo. Он не отрисовывает графики, не читает и не изменяет LAS-файлы, а возвращает новый immutable `PlotWorkspace` с обновленным `PlotViewportState`.

### 5.2 Основные модели

- `PlotNavigationBounds` — полный допустимый диапазон глубин для ограничения zoom/pan.
- `PlotNavigationConfig` — параметры чувствительности wheel zoom, zoom out, pan, минимального окна и размера истории.
- `PlotNavigationHistory` — undo/redo history для viewport-состояний.
- `PlotNavigationState` — текущий workspace вместе с bounds и history для Session State.
- `PlotBoxZoomRequest` — нормализованный запрос выделения прямоугольной области.
- `PlotPanRequest` — нормализованный запрос перемещения графика по глубине.

### 5.3 Реализованные функции

- инициализация navigation state из Plot Workspace;
- проверка и построение navigation bounds;
- zoom колесом мыши относительно anchor depth;
- zoom in / zoom out с ограничением по полному диапазону данных;
- box zoom по выбранному интервалу глубины;
- pan по delta или fraction;
- reset zoom до полного диапазона;
- undo/redo истории viewport;
- формирование serializable manifest для Streamlit Session State и debug panel.

### 5.4 Инженерные ограничения

- оригинальный LAS не изменяется;
- работа выполняется только с immutable workspace model;
- zoom/pan не позволяют выйти за полный диапазон данных;
- минимальное окно zoom защищает UI от нулевого или слишком малого масштаба;
- crosshair автоматически ограничивается новым viewport;
- история viewport ограничивается `max_history`, чтобы не раздувать Session State.

### 5.5 Acceptance Criteria

Mouse Zoom & Navigation считается готовым, если:

1. колесо мыши уменьшает или увеличивает текущий интервал глубин;
2. anchor depth сохраняет положение относительно окна zoom;
3. box zoom принимает прямой и обратный выбор интервала;
4. pan сохраняет текущую высоту окна;
5. reset возвращает полный диапазон;
6. undo/redo восстанавливают предыдущие viewport-состояния;
7. операции не мутируют исходный workspace;
8. все операции ограничены navigation bounds.

---

## 6. Plot Studio Manual X/Y Scale Backend

Реализован backend-слой ручного масштабирования Plot Studio 2.0: `projects/plot_studio_manual_scale.py`.

### 6.1 Назначение

Модуль обеспечивает ручную настройку масштаба без привязки к конкретному renderer-у. UI может использовать этот слой для sidebar-полей, диалогов настройки планшета, горячих клавиш и будущих preset-шаблонов.

### 6.2 Основные модели

- `PlotManualScaleConfig` — инженерные ограничения для глубины, минимального окна и X-диапазона.
- `PlotManualDepthScaleRequest` — запрос ручного Y/depth диапазона для синхронного планшета.
- `PlotManualCurveScaleRequest` — запрос ручного X-диапазона для кривой, мнемоники или трека.
- `PlotManualScaleResult` — результат операции для UI status panel и Operation Journal.

### 6.3 Реализованные функции

- ручная установка общего диапазона глубины `Depth From / Depth To`;
- ручное задание major/minor шага сетки по глубине;
- ручная установка X-min/X-max для выбранной кривой;
- применение X-scale к группе кривых по track id или mnemonic;
- поддержка `linear` и `log` шкал;
- проверка log-шкалы на положительный минимум;
- переключение кривой обратно в auto range;
- формирование serializable manifest для UI, тестов и журнала операций;
- сохранение immutable-подхода: исходный `PlotWorkspace` не мутируется.

### 6.4 Инженерные ограничения

- оригинальный LAS не изменяется;
- операции работают только с renderer-independent `PlotWorkspace`;
- глубина ограничена допустимым инженерным диапазоном;
- X-min обязан быть меньше X-max;
- для log-шкалы X-min должен быть больше нуля;
- при изменении depth scale crosshair автоматически ограничивается новым интервалом;
- если подходящие кривые не найдены, возвращается контролируемый result без падения UI.

### 6.5 Acceptance Criteria

Manual X/Y Scale считается готовым, если:

1. ручной depth interval применяется ко всем синхронным трекам;
2. major/minor grid step сохраняется в viewport depth range;
3. ручной X-scale применяется только к выбранным кривым;
4. auto range можно восстановить отдельно;
5. log scale валидируется до построения графика;
6. исходный workspace остается неизменным;
7. manifest содержит depth scale и curve scale состояние для UI/debug;
8. модуль покрыт unit-тестами.

---

## 7. Plot Studio Synchronized Scrolling Backend

Реализован backend-слой синхронной прокрутки Plot Studio 2.0: `projects/plot_studio_sync_scroll.py`.

### 7.1 Назначение

Модуль управляет общей вертикальной прокруткой планшета по измеренной глубине. Он не отрисовывает графики, не читает и не изменяет LAS-файлы, а возвращает новый immutable `PlotWorkspace` с обновленным общим `PlotViewportState`.

### 7.2 Основные модели

- `PlotScrollConfig` — параметры чувствительности wheel/keyboard/page scrolling и минимального окна.
- `PlotScrollRequest` — нормализованный запрос прокрутки по направлению, метрам или доле текущего окна.
- `PlotSynchronizedTrackState` — состояние глубинного окна для каждого видимого трека.
- `PlotScrollResult` — результат операции для UI status panel, Session State и Operation Journal.

### 7.3 Реализованные функции

- инициализация synchronized scrolling state;
- построение синхронных track states для всех видимых треков;
- прокрутка вверх/вниз по абсолютному `delta_m`;
- прокрутка по доле текущего окна для wheel/keyboard/page сценариев;
- центрирование viewport вокруг выбранной глубины;
- выравнивание текущего viewport по границам полного диапазона данных;
- ограничение выхода за верхнюю и нижнюю границы данных;
- автоматическое ограничение crosshair новым интервалом глубины;
- формирование serializable manifest для UI/debug/tests.

### 7.4 Инженерные ограничения

- оригинальный LAS не изменяется;
- операции работают только с renderer-independent `PlotWorkspace`;
- все видимые треки получают один и тот же depth interval;
- viewport не может выйти за `PlotNavigationBounds`;
- высота окна сохраняется при обычной прокрутке;
- при достижении границы возвращается контролируемый result без аварийного падения UI;
- исходный workspace остается неизменным.

### 7.5 Acceptance Criteria

Synchronized Scrolling считается готовым, если:

1. прокрутка изменяет общий depth interval для всех видимых треков;
2. высота текущего viewport сохраняется;
3. верхняя и нижняя границы данных не нарушаются;
4. scroll-to-depth центрирует окно там, где это возможно;
5. crosshair автоматически ограничивается текущим viewport;
6. manifest содержит viewport и synchronized track states;
7. операции не мутируют исходный workspace;
8. модуль покрыт unit-тестами.

## Phase B — Professional Track Layout

Implemented backend module: `projects/plot_studio_track_layout.py`.

The Professional Track Layout layer prepares a renderer-independent tablet geometry for Plot Studio 2.0.

Responsibilities:

- normalize visible Plot Studio tracks into ordered layout items;
- calculate pixel width, percentage width, left and right boundaries;
- support a dedicated depth track on the left, right or hidden mode;
- freeze the depth track for professional synchronized scrolling;
- preserve original `PlotWorkspace` and LAS data without mutation;
- provide UI/export manifests and diagnostic table rows;
- validate canvas width, gutters, minimum track width and depth-track placement.

The module is used as a base for future Tablet Templates, print layout, export layout and annotation placement.

## Plot Studio Export Engine

Plot Studio Export Engine является backend-слоем экспорта профессиональных планшетов Plot Studio 2.0. Модуль не изменяет исходные LAS-файлы и работает только с неизменяемыми объектами `PlotWorkspace` и `PlotTrackLayoutResult`.

### Назначение

- формирование единого export manifest для UI, журнала операций и последующего Report Studio;
- экспорт планшетов в PDF, PNG, SVG и TIFF;
- проверка DPI, масштаба, размеров страницы и списка форматов;
- защита от случайной перезаписи файлов;
- сохранение JSON-манифеста рядом с экспортированными артефактами;
- подготовка стабильного API для будущего подключения Plotly/Kaleido и профессионального print engine.

### Основные компоненты

- `PlotExportConfig` — настройки экспорта: форматы, DPI, масштаб, размер страницы, легенда, заголовок, metadata, overwrite;
- `PlotExportArtifact` — описание одного созданного файла;
- `PlotExportManifest` — полный манифест экспорта с геометрией планшета и списком сообщений;
- `PlotExportResult` — итог выполнения операции экспорта;
- `validate_plot_export_config()` — нормализация и проверка настроек;
- `build_plot_export_manifest()` — подготовка манифеста без записи файлов;
- `export_plot_studio()` — запись экспортных файлов и JSON-манифеста;
- `build_plot_export_result_manifest()` — сериализация результата для UI и Operation Journal.

### Правила безопасности

- оригинальные LAS-файлы не читаются и не изменяются;
- экспорт выполняется только на основе подготовленного workspace/layout;
- существующие файлы не перезаписываются без `overwrite=True`;
- все размеры и числовые параметры проходят проверку на конечность и допустимый диапазон;
- результат экспорта может быть записан в Operation Journal.

### Поддерживаемые форматы

- PDF;
- PNG;
- SVG;
- TIFF.

Текущая реализация содержит легковесные встроенные writers для стабильного backend API и тестов. В дальнейшем renderer может быть заменен на Plotly/Kaleido или специализированный print engine без изменения публичного интерфейса Export Engine.

## Plot Studio Annotation Layer

Plot Studio Annotation Layer является renderer-independent backend-слоем для подготовки инженерных аннотаций планшета Plot Studio 2.0. Модуль работает только с объектами `PlotWorkspace` и `PlotTrackLayoutResult`, не читает и не изменяет исходные LAS-файлы.

### Назначение

- подготовка маркеров глубины, интервалов, зон и текстовых комментариев;
- привязка аннотаций к конкретному треку или ко всему планшету;
- расчет координат аннотаций в пикселях для UI, печати и Export Engine;
- отсечение аннотаций по текущему viewport глубины;
- фильтрация скрытых, заблокированных, глобальных и некорректно привязанных аннотаций;
- формирование serializable manifest для UI, Operation Journal, Report Studio и будущего Print Engine.

### Основные компоненты

- `PlotAnnotation` — исходная аннотация пользователя или интерпретации;
- `PlotAnnotationPlacement` — рассчитанное положение аннотации в координатах canvas;
- `PlotAnnotationLayerConfig` — настройки высоты canvas, отступов и правил фильтрации;
- `PlotAnnotationLayerResult` — итоговый слой аннотаций;
- `validate_plot_annotations()` — проверка типов, глубин, идентификаторов и обязательных подписей;
- `build_plot_annotation_layer()` — построение renderer-ready слоя аннотаций;
- `build_plot_annotation_manifest()` — сериализация слоя для UI/export/journal;
- `build_plot_annotation_table()` — таблица для Streamlit-интерфейса и диагностики.

### Типы аннотаций

- `marker` — одиночная глубинная отметка;
- `interval` — интервал глубин;
- `zone` — выделенная зона/заливка;
- `text` — текстовый комментарий на заданной глубине.

### Правила безопасности

- исходный `PlotWorkspace` остается неизменным;
- оригинальные LAS-файлы не читаются и не модифицируются;
- аннотации за пределами текущего viewport пропускаются или обрезаются;
- неизвестные track id не приводят к аварийному падению UI, а возвращаются как сообщения результата;
- duplicate annotation id блокируются на уровне валидации;
- результат можно безопасно передать в Export Engine, Report Studio и Operation Journal.

### Acceptance Criteria

Annotation Layer считается готовым, если:

1. поддерживаются marker, interval, zone и text;
2. аннотации могут быть привязаны к треку или ко всему планшету;
3. координаты рассчитываются относительно текущего depth viewport;
4. интервалы корректно обрезаются по границам viewport;
5. скрытые, заблокированные и глобальные аннотации фильтруются настройками;
6. неизвестные треки возвращают контролируемые сообщения;
7. manifest и table rows сериализуются без renderer-зависимостей;
8. модуль покрыт unit-тестами.

## Plot Studio Printing Engine

Plot Studio Printing Engine является renderer-independent backend-слоем для подготовки профессиональной печати планшетов Plot Studio 2.0. Модуль не строит изображение напрямую, а формирует проверенный print manifest для Streamlit UI, Export Engine, Report Studio и Operation Journal.

### Назначение

- подготовка планшета к печати на A4/A3/A2/A1/A0/Letter;
- поддержка портретной и альбомной ориентации;
- расчет размеров страницы, полей и печатной области в миллиметрах и пикселях;
- поддержка режимов масштаба `fit_width`, `fit_page`, `fixed_scale`;
- расчет количества страниц по глубине;
- разбиение глубинного интервала на страницы;
- подготовка таблицы страниц для UI-preview;
- сохранение параметров заголовка, футера, легенды, номеров страниц и повторения depth-track.

### Основные компоненты

- `PlotPrintConfig` — настройки страницы, DPI, полей, масштаба и печатных опций;
- `PlotPrintPage` — одна логическая страница печати с диапазоном глубины;
- `PlotPrintManifest` — полный манифест печати;
- `PlotPrintJob` — валидированный descriptor задания печати;
- `validate_plot_print_config()` — нормализация и проверка настроек печати;
- `build_plot_print_manifest()` — подготовка print-ready manifest;
- `create_plot_print_job()` — создание задания печати;
- `build_plot_print_manifest_dict()` — сериализация manifest для UI/export/journal;
- `build_plot_print_page_table()` — таблица страниц для Streamlit preview.

### Правила безопасности

- оригинальные LAS-файлы не читаются и не изменяются;
- исходный `PlotWorkspace` не мутируется;
- печать выполняется только на основе подготовленного workspace/layout;
- все числовые параметры проходят проверку на конечность и допустимый диапазон;
- недопустимые поля страницы блокируются до формирования задания;
- пустой workspace возвращает controlled not-ready job вместо аварийного падения UI.

### Acceptance Criteria

Printing Engine считается готовым, если:

1. поддерживаются основные инженерные форматы страниц;
2. корректно рассчитываются ориентация, поля и печатная область;
3. поддерживаются fit-width, fit-page и fixed-scale режимы;
4. длинный планшет разбивается на страницы по глубине;
5. manifest сериализуется без renderer-зависимостей;
6. empty workspace обрабатывается безопасно;
7. модуль покрыт unit-тестами.
