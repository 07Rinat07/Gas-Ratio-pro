# Visualization Prefetch Priority v114

Viewport prefetch now prioritizes work by recent navigation direction and viewport proximity.

- Tasks in the current pan direction receive the highest priority.
- Tasks with equal priority are ordered by distance from the active viewport.
- Queue capacity still removes the least useful pending task.
- Existing cancellation, deduplication and process limits remain unchanged.
- `priority_pops` is exposed in scheduler metrics.
