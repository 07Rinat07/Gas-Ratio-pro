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
