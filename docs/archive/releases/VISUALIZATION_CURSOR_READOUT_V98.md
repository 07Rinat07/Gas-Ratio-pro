# Visualization Cursor Readout v98

Version 98 adds a renderer-neutral cursor layer on top of InteractiveViewport,
Hit Testing Engine and Spatial Index.

The cursor engine converts screen Y to depth, resolves nearby primitives and
returns a deterministic serializable readout for UI adapters. It contains no UI
or renderer-specific logic.
