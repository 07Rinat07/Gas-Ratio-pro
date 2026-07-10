# Visualization Track Engine v82

## Purpose

The Track Engine owns renderer-neutral track state after Scene and Layout have
been prepared. It prevents SVG, PDF, Canvas and Streamlit renderers from making
independent decisions about track ordering, visibility, active focus, printable
state or shared depth viewport metadata.

## Pipeline position

```text
Source Adapter
Domain Model
Scene
Layout
Axis and Grid Model
Track Model
Render Model
Renderer
```

## Contracts

`VisualizationTrackCollection` contains:

- ordered track models;
- visible track identifiers;
- active track identifier;
- shared-depth viewport flag;
- validation issues.

Each `VisualizationTrackModel` contains:

- stable id, title and order;
- visible, printable and pinned state;
- group and width metadata;
- attached layer ids;
- track, header, axis and plot regions;
- shared depth viewport metadata.

## Architectural rule

UI and renderer code must not calculate track visibility, ordering or depth
viewport state. They consume the Track Model produced by the pipeline.

## Next step

Move curve and interval overlay geometry into Render Model primitives. This will
allow the SVG renderer to consume only Render Model output and retire the
remaining compatibility path that reads scene layers directly.
