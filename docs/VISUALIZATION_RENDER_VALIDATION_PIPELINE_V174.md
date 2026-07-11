# Visualization Render Validation Pipeline v174

This roadmap-aligned increment integrates renderer-neutral pre-render validation into the Visualization Engine scene pipeline.

The validator runs after Render Model construction and before SVG/PDF rendering. It verifies:

- valid canvas geometry;
- clip regions contained by the canvas;
- primitive geometry and clip references;
- unclipped primitives contained by the canvas;
- collisions between high-level curve labels and track titles;
- print content contained by printable page bounds;
- print source geometry matching the Render Model canvas.

The result is exposed in `pipeline.validation.render_validation` and participates in the pipeline `ok` status. No UI or renderer-specific business logic is introduced.
