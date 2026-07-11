# Visualization Performance Engine v91

## Purpose

The performance layer prevents repeated construction of an identical renderer-neutral Render Model during one application process. It remains independent from Streamlit and concrete SVG/PDF backends.

## Pipeline position

```text
Domain Model -> Scene -> Layout -> Axis/Grid -> Track Model -> Label/Legend -> Print Layout -> Performance -> Render Model -> Renderer
```

## Implemented contracts

- `VisualizationPerformanceEngine` creates a deterministic SHA-256 cache key from Scene, Layout, Axis/Grid, Track, Label/Legend and Print Layout contracts.
- `VisualizationRenderModelCache` provides a bounded in-memory LRU cache.
- `VisualizationPerformanceProfile` exposes cache hit state, cache capacity, source/render point counts and reduction metadata.
- Cached values are restored through `VisualizationRenderModel.from_dict()` so renderers continue receiving the same typed contract.
- `performance_cache: false` disables reuse for diagnostics or strict one-shot execution.

## Safety

The cache stores only JSON-serializable renderer-neutral contracts. It does not store DataFrames, UI objects or source file handles.

## Next step

Add viewport-aware adaptive downsampling and incremental geometry invalidation for large LAS datasets.
