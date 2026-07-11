# LAS Visualization Renderer Ready Payload V66

## Purpose

This increment extends the renderer-neutral LAS visualization contract with data that a UI renderer can consume directly. The service now prepares legend entries, default visible tracks and a compact plot summary outside Streamlit, so the UI does not need to inspect curves, overlays or styles to decide what to render.

## Added

- Renderer-ready `legend` payload for curves and interval overlays.
- `visible_tracks` list for default printable track visibility.
- Compact `plot_summary` with depth range, track count, curve count, overlay count and renderer readiness.
- Regression coverage for legend, visible tracks and plot summary.

## Contract guarantees

- Legend labels and styles are prepared by the service layer, not by UI code.
- Renderers can display default track visibility without recalculating track state.
- Plot summary cards can be rendered from a small stable payload.
- Raw LAS dataframes remain excluded from visualization payloads.

## QA

Validated with targeted LAS visualization payload tests and release export QA.
