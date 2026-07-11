# Workspace Reset v36

Modern UI needs a safe reset action so stale tables, graphs, diagnostics and export previews do not remain after the user changes data or wants to clear the working state.

## Added

- `core.workspace_reset.WorkspaceResetController`
- reset preview without mutating state
- reset modes: `derived`, `las_context`, `workspace_context`, `full_context`
- confirmation gate for context-changing actions
- preservation of global settings such as theme and EULA status

## Engineering rule

Reset actions clear derived application state only. They do not delete files from disk. Destructive project-file operations must remain in repository/storage services and require separate confirmation.
