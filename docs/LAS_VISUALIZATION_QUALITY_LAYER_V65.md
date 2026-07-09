# LAS Visualization Quality Layer V65

## Purpose

This increment extends the renderer-neutral LAS visualization contract with explicit sampling and quality metadata. The Workbench can now render large LAS datasets without passing raw dataframes into the UI and can explain whether curve data was decimated, incomplete or affected by depth gaps.

## Added

- Global `sampling_profile` for LAS visualization payloads.
- Per-curve `sampling` metadata.
- Per-curve `quality` metadata.
- Payload-level `data_quality` summary.
- Depth-gap detection based on expected LAS depth step.
- Missing-point accounting after numeric normalization.

## Contract guarantees

- Raw dataframes are never included in renderer payloads.
- First and last sampled points are preserved during decimation.
- Renderers receive enough metadata to warn users about incomplete curves.
- Print/SVG/PDF rendering can use the same lightweight payload as interactive UI rendering.

## QA

Validated with targeted LAS visualization, Workbench provider and tool action tests, plus release export QA.
