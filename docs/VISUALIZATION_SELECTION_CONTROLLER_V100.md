# Visualization Selection Controller v100

Version 100 adds a renderer-neutral controller around the immutable selection engine.

The controller provides bounded undo/redo history, redo-branch invalidation, no-op suppression, reset to the initial selection, history clearing, and a compact serializable snapshot for Workspace Session and Event Bus integration.

UI adapters remain responsible only for producing `SelectionCommand` values and rendering `SelectionState`.
