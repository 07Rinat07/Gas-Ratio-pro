# LAS Viewer Overlay Workspace Session v133

The active LAS Viewer overlay preset is now part of the lightweight Workspace Session contract.

- `workspace_session_active_overlay_preset` is captured, saved and restored.
- `LasViewerOverlayPresetRuntime` can bind to application state through `workspace_state`.
- Applying, restoring or falling back to another preset updates the workspace state automatically.
- Existing session JSON files remain compatible and default to `Default` when the field is absent.
