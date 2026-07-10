# Visualization prefetch anti-oscillation v118

Version 118 limits adaptive prefetch distance changes with two safeguards:

- a configurable cooldown measured in stable telemetry windows;
- confirmation of direction reversals before switching from expansion to shrinkage or back.

The scheduler exposes `cooldown_holds`, `reversal_holds` and
`last_distance_direction` for diagnostics. UI code remains free of tuning logic.
