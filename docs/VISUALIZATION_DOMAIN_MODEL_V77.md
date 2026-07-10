# Visualization Domain Model v77

## Purpose

The Visualization Domain Model separates engineering visualization data from source formats and renderer implementations.

The pipeline is now:

```text
LAS or future source
        ↓
Source adapter
        ↓
Visualization Domain Model
        ↓
Scene Context
        ↓
Visualization Scene
        ↓
Layout Engine next
        ↓
Renderer
```

## Contract

The domain model contains:

- logical tracks;
- normalized curve series;
- interpreted depth intervals;
- shared depth metadata;
- quality flags;
- lightweight presentation metadata.

The contract does not contain raw DataFrame objects, Streamlit state, matplotlib figures or renderer geometry.

## Current adapter

`VisualizationDomainModelAdapter` converts the existing LAS visualization payload into `VisualizationDomainModel`.

Future DLIS, WITSML, CSV and database adapters can produce the same model without changing the scene pipeline or renderers.

## Next step

Implement the renderer-neutral Layout Engine. It must consume `VisualizationScene` and produce a geometry-ready render model for SVG, PDF and interactive renderers.
