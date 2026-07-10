# Visualization Axis and Grid Engine v81

## Purpose

This increment adds renderer-neutral axis and grid preparation between Layout and Render Model.
Concrete renderers no longer need to calculate tick positions or grid coordinates from LAS data.

## Pipeline

```text
Source Adapter
Domain Model
Scene
Layout
Axis and Grid Model
Render Model
Renderer
```

## Contracts

- `AxisTick` stores value, prepared coordinate, label and major/minor role.
- `AxisModel` describes shared depth axes and per-curve horizontal axes.
- `GridLine` stores ready line coordinates and the source axis reference.
- `VisualizationAxisGridModel` contains deterministic axes, grid lines and diagnostics.

## Supported scales

- Shared linear depth axis with major and minor ticks.
- Linear curve axes with formatted tick labels.
- Logarithmic curve axes with decade and minor ticks.

## Architectural boundaries

- No Streamlit, matplotlib, SVG or PDF imports are used.
- No raw LAS DataFrame enters the model.
- Tick and grid geometry is calculated once before rendering.
- Render Model converts axes and grids to printable line and text primitives.

## Next increment

Implement Track and Curve primitives so curve polylines and interval bands are also generated in Render Model rather than inside the compatibility SVG scene renderer.
