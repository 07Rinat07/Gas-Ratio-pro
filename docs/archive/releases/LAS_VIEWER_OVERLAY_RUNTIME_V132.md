# LAS Viewer Overlay Preset Runtime v132

Version 132 adds a renderer-neutral runtime that binds overlay presets to an
active LAS Viewer session. A preset can be applied or hot-reloaded without
restarting the viewer. Repository fingerprints prevent redundant updates, and
missing active presets fall back deterministically to the default preset.

The runtime also generates interaction overlays through the existing overlay
engine, keeping style resolution and synchronization outside UI adapters.
