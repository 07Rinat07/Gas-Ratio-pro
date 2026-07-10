# Visualization Curve and Overlay Render Model v83

## Purpose

This increment removes curve and interpreted interval geometry from the SVG renderer.
The renderer now consumes prepared `VisualizationRenderModel` primitives when it receives
a `visualization.scene.pipeline.result` contract.

## Added primitives

- `polyline` primitives for LAS curves;
- clipped `rectangle` primitives for interpreted interval overlays;
- clipped `text` primitives for overlay labels;
- source-layer metadata for renderer diagnostics and QA.

## Pipeline responsibility

The Render Model builder now performs:

- linear and logarithmic curve normalization;
- depth-to-pixel mapping;
- plot clipping assignment;
- interval depth-band geometry;
- deterministic primitive ordering.

The SVG renderer only serializes rectangles, lines, text and polylines. It no longer
reads curve points or interval depth ranges from Scene for normal pipeline rendering.
A legacy Scene fallback remains temporarily for compatibility with direct scene callers.

## Next step

Add explicit curve-segment handling for NaN gaps, clipping at viewport boundaries and
optional fill primitives before removing the legacy Scene rendering path.
