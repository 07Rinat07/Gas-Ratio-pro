# Visualization Prefetch Tuning State v119

The viewport prefetch scheduler can now export and restore its adaptive tuning state.
Only stable telemetry fields are persisted; pending tasks, generations and runtime counters remain transient.

This allows Workspace Session or LAS Viewer persistence to continue adaptive prefetch behavior after restart without replaying old navigation events.
