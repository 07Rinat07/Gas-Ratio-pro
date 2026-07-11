# Visualization Spatial Index v97

Version 97 adds a reusable renderer-neutral uniform-grid spatial index for hit testing.

## Scope

- Conservative bounding boxes for polyline, rectangle, line and text primitives.
- Configurable uniform-grid buckets.
- Point-plus-tolerance candidate lookup.
- Compatibility validation against the source render model.
- Optional integration with `VisualizationHitTestingEngine`.
- Serializable diagnostics without exposing bucket or geometry payloads.

The index is built once per render model and reused for cursor movement queries. Exact geometric hit testing remains in `VisualizationHitTestingEngine`; the index only reduces the candidate set.
