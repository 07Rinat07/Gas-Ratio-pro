# Visualization Renderer Parity v87

## Purpose

This increment starts renderer parity without pretending that PDF and HTML
primitive renderers already exist. The SVG adapter is now the reference
implementation over the renderer-neutral Render Model.

## Implemented

- `VisualizationRendererParityValidator` compares a renderer artifact with:
  - printable and visible Render Model primitives;
  - clip regions;
  - Print Layout application state.
- SVG output uses the prepared page bounds from `VisualizationPrintLayout`.
- Source pixel geometry is transformed into physical page points using the
  configured DPI and prepared content scale.
- Renderer output reports primitive count, clip count, page size and whether
  Print Layout was applied.

## Boundaries

The SVG renderer does not calculate axes, tracks, curves, labels or page
placement. It serializes prepared primitives and applies the prepared page
transform. PDF and HTML parity are intentionally left for later adapters.

## Next step

Add a PDF primitive renderer over the same Render Model and verify geometry
parity through the shared validator.
