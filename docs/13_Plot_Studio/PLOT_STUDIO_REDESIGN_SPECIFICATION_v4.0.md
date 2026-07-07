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
