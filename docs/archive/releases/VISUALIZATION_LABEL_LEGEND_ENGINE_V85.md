# Visualization Label and Legend Engine v85

## Purpose

This increment adds renderer-neutral text and legend contracts to Visualization Engine 2.0. Concrete renderers no longer need to inspect LAS layers to decide which curve names, units or interval meanings should be displayed.

## Pipeline

```text
Source Adapter
  -> Domain Model
  -> Scene
  -> Layout
  -> Axis and Grid
  -> Track Model
  -> Label and Legend Model
  -> Render Model
  -> Renderer
```

## Added contracts

- `VisualizationLabel`
- `VisualizationLegendItem`
- `VisualizationLabelLegendModel`
- `VisualizationLabelLegendEngine`

## Label rules

- Track titles and curve labels are placed before renderer execution.
- Curve labels include engineering units when available.
- Label count per track is bounded to prevent unreadable headers.
- Long labels are truncated deterministically.
- Basic collision spacing is applied in axis/header regions.
- UI and renderer objects are never stored in the contract.

## Legend rules

- Curve legend items contain mnemonic, unit, line color and width.
- Interval legend items contain label, fill color and confidence when available.
- Duplicate interval legend entries inside the same track are removed.
- Legend metadata remains renderer-neutral and serializable.

## Compatibility

The SVG renderer continues to consume `VisualizationRenderModel`. Label geometry is converted to text primitives by the Render Model builder. Legend items are exposed in Render Model metadata for the future dedicated legend layout and print renderer stages.

## Next step

Implement Print Layout Engine and dedicated legend placement primitives for page formats, margins and pagination.
