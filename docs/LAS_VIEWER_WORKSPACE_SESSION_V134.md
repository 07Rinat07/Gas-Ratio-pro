# LAS Viewer Workspace Session v134

The LAS Viewer can now persist and restore its compact renderer-neutral state through Workspace Session.

Persisted state includes viewport, cursor, selection, track layout, curve visibility, active track and active curve. Raw LAS samples, render models and caches are excluded.

`LasViewerWorkspaceSessionBridge` validates the active project and LAS identifiers before restoration and safely rejects missing, invalid or mismatched state.
