# Visualization Render Model Foundation v80

## Назначение

Первый программный слой Render Model реализован между `VisualizationLayout` и будущими renderer backend. Он принимает только сериализованные Scene и Layout contracts и формирует детерминированный набор renderer-neutral примитивов.

## Реализованные контракты

- `RenderClipRegion` — именованная прямоугольная область clipping.
- `RenderPrimitive` — универсальная команда рисования с `kind`, `z_index`, `track_id`, `clip_id` и сериализуемым payload.
- `VisualizationRenderModel` — canvas, clip regions, упорядоченные примитивы, diagnostics и metadata.
- `VisualizationRenderModelBuilder` — построение структурных примитивов canvas и tracks.

## Текущий scope

На этом инкременте Render Model формирует:

- фон canvas;
- фон и границу каждого track;
- заголовок track;
- clip region plot area;
- безопасную диагностическую карточку для пустого layout;
- diagnostics о source layers, которые будут конвертированы следующими этапами.

Кривые, интервалы, оси и сетка пока не переводятся в финальные drawing primitives. Это намеренно зафиксировано diagnostic `render_model_pending_source_layers` и не скрывается от QA.

## Pipeline

```text
Source Adapter
Domain Model
Scene Context
Scene
Layout
Render Model
Validation
```

Текущий SVG scene renderer остается compatibility path и пока читает Scene/Layout. Переключение SVG на Render Model выполняется только после появления curve, overlay, axis и grid primitives.

## Архитектурные гарантии

- Render Model не импортирует Streamlit, matplotlib, pandas или report renderer.
- Примитивы и clip regions сериализуются в обычные словари.
- Порядок примитивов стабилен: `z_index`, затем `track_id`, затем `id`.
- Raw DataFrame и UI objects не включаются.
- Пустой layout дает диагностическую модель, а не исключение.

## Следующий шаг

Реализовать Axis and Grid Model поверх `line` и `text` primitives: major/minor ticks, depth labels, linear/log curve axes и print-safe grid.
