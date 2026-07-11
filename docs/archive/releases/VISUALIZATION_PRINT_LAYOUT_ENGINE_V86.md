# Visualization Print Layout Engine v86

## Purpose

`VisualizationPrintLayoutEngine` prepares physical page geometry before a PDF,
SVG or other export renderer runs. The engine does not draw content and does not
read LAS data. It converts the existing visualization layout into a stable,
renderer-neutral page contract.

## Supported page settings

- Page sizes: A4, A3, A2 and A1.
- Orientation: portrait and landscape.
- Scale modes: fit page, fit width and actual size.
- Configurable margins in millimetres.
- Legend placement: bottom, right or none.
- Configurable source DPI.

## Output contract

The `visualization.print.layout` contract includes:

- physical page dimensions in millimetres;
- page and printable bounds in points;
- source visualization bounds;
- calculated content scale and centred content placement;
- reserved legend region;
- page count and QA metadata.

The current increment intentionally produces one deterministic page. Multi-page
pagination remains a later Print Layout increment.

## Pipeline position

```text
Domain Model
Scene
Layout
Axis and Grid
Track Model
Label and Legend
Print Layout
Render Model
Renderer
```

`VisualizationRenderModel` carries the prepared print layout in metadata so
export renderers can consume the same page contract without recalculating page
sizes, margins or scale.
