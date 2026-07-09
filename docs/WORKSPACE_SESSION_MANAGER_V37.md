# Workspace Session Manager v37

`WorkspaceSessionManager` adds lightweight session capture and restore for the Modern UI.

The session stores only user workspace context:

- active project, well, LAS and workspace ids;
- opened files;
- selected interpreted intervals;
- active report and active plot ids;
- recent exports;
- window layout;
- user profile.

It does **not** store heavy transient artifacts such as LAS dataframes, calculated tables, rendered Plotly figures or raw interpretation dumps. Those artifacts must be rebuilt from project data after restore.

## Engineering purpose

The user can close the program and reopen the last workspace without losing orientation: the same well, selected intervals, report, plot and layout can be restored.

## Design rule

Workspace sessions are UI/workflow descriptors, not geological data stores.
