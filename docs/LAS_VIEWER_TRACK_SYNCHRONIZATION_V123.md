# LAS Viewer Track Synchronization v123

Version 123 adds a renderer-neutral service that projects one shared depth
cursor across all visible LAS track plot regions. The service converts screen Y
to depth through `InteractiveViewport` and returns ready-to-render horizontal
segments for each track. UI adapters do not calculate depth or track bounds.

The contract supports serialized render models and viewport state, preserves
requested track order, reports missing plot regions, and detects inconsistent
track plot geometry.
