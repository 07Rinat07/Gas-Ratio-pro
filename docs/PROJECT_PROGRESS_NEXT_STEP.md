# Next Step

Completed: project-scoped manual cleanup for quarantined report-preview metadata.

The Report Preview storage diagnostics now exposes an **Очистить карантин** action only when quarantined files exist. The action removes only `.corrupt-*` metadata for the active project, preserves the primary snapshot and backup, logs the actual result, and reruns the UI to refresh storage health.

Next recommended increment: bounded PDF page-thumbnail preview with a strict page limit, cache signature binding, and a safe fallback when the optional PDF rasterizer is unavailable.
