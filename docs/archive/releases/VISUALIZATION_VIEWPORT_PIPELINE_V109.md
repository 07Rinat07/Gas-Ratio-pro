# Visualization Viewport Pipeline v109

Version 109 adds a renderer-neutral adapter that applies the interactive depth
viewport before the standard scene pipeline is executed.

The adapter:

- clamps viewport bounds to the LAS depth domain;
- filters curve samples to the visible interval;
- interpolates boundary samples for continuous curves;
- clips interval overlays to the visible interval;
- keeps UI adapters free from visualization calculations;
- returns a serializable performance/profile contract.

Main module: `services/visualization_viewport_pipeline.py`.
