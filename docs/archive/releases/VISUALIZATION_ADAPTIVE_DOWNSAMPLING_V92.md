# Visualization Adaptive Downsampling v92

## Purpose

This increment adds viewport-aware reduction of dense LAS curve geometry before renderer-neutral polyline primitives are created.

## Contract

The pipeline accepts optional performance settings:

```python
{
    "performance_options": {
        "max_points_per_pixel": 1.5,
        "minimum_render_points": 64,
    }
}
```

The settings are included in the Render Model cache key. Changing sampling density therefore cannot incorrectly reuse geometry produced with another performance profile.

## Strategy

`VisualizationCurveQualityEngine` calculates a point budget from the current plot height. Dense continuous segments are reduced with an extrema-preserving bucket strategy. The first and last points remain stable and local low/high X values are retained in depth order.

Quality metadata records the source count, render count, point budget and number of removed points. Renderers consume the prepared polyline primitives and contain no downsampling logic.

## Cache invalidation

`VisualizationRenderModelCache.invalidate()` and `VisualizationPerformanceEngine.invalidate()` remove one exact geometry contract without clearing unrelated cached models.

## Safety

- No raw DataFrame objects are cached.
- Viewport and sampling options affect the deterministic cache key.
- Invalid points and depth gaps are segmented before downsampling.
- SVG and PDF continue to consume the same Render Model geometry.
