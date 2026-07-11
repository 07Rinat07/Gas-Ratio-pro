# Visualization Render Model Roadmap v79

## Назначение

Render Model вводится между `VisualizationLayout` и конкретными renderer. Его задача —
преобразовать инженерную сцену и рассчитанную геометрию в стабильный набор
renderer-neutral примитивов. После этого SVG, PDF, Canvas, Streamlit и другие backend
только отображают готовые команды и не выполняют инженерные или геометрические расчеты.

## Целевая цепочка

```text
Source Adapter
    ↓
Visualization Domain Model
    ↓
Visualization Scene
    ↓
Visualization Layout
    ↓
Visualization Render Model
    ↓
SVG / PDF / Canvas / Streamlit / PNG
```

## Границы ответственности

### Domain Model

Хранит нормализованные инженерные объекты: треки, кривые, интервалы и интерпретации.
Не содержит координат экрана и renderer-специфичных данных.

### Scene

Определяет видимые инженерные слои, порядок треков, диапазон глубины и состав сцены.
Не рассчитывает финальные координаты примитивов.

### Layout

Рассчитывает геометрию canvas, треков, plot/header/axis regions и преобразование глубины
в координату. Не формирует SVG path, PDF-команды или HTML.

### Render Model

Формирует упорядоченные примитивы:

- polyline/path для кривых;
- line для осей, ticks и сетки;
- rectangle для интервалов и фона;
- text для подписей и легенды;
- clip region для ограничения рисования;
- group/layer metadata для стабильного z-order;
- diagnostics для QA и fallback.

### Renderer

Только переводит примитивы в конкретный backend. Renderer не читает LAS payload,
Domain Model или Scene и не пересчитывает layout.

## План реализации

### Первый инкремент

- базовые dataclass/contract примитивов;
- `VisualizationRenderModel`;
- `VisualizationRenderModelBuilder`;
- стабильный порядок слоев;
- clipping metadata;
- безопасная модель для пустой сцены;
- тесты сериализации и детерминированности.

### Следующие инкременты

1. Axis and Grid Model поверх line/text primitives.
2. Track and Curve primitives.
3. Label collision policy и Legend primitives.
4. Print Layout и parity SVG/PDF.
5. Large LAS optimization, batching и path simplification.

## Совместимость

Текущий `VisualizationSvgSceneRenderer` сохраняется как временный compatibility path.
После появления Render Model будет добавлен новый adapter, который потребляет только
`VisualizationRenderModel`. Старый прямой путь `Scene → SVG` удаляется только после
регрессионной проверки отчетов и export QA.

## Критерии готовности

- одинаковый Render Model дает эквивалентный SVG/PDF результат;
- renderer не обращается к Domain Model или Scene;
- геометрия не рассчитывается внутри renderer;
- порядок примитивов детерминирован;
- пустые и некорректные сцены дают диагностический, а не аварийный результат;
- модель сериализуется без raw DataFrame и UI-объектов.
