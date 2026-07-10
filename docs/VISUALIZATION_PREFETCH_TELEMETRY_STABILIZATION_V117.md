# Visualization prefetch telemetry stabilization v117

Version 117 prevents adaptive prefetch distance from reacting to duplicate or
undersized telemetry windows.

Changes:
- cumulative cache counters are converted to per-observation deltas;
- repeated counters cannot repeatedly change the distance ratio;
- small windows are ignored until `minimum_telemetry_samples` is reached;
- hit rate is smoothed with an EWMA coefficient;
- shrink/expand thresholds are configurable;
- scheduler diagnostics expose holds, updates and smoothed hit rate.

Optional configuration:

```python
payload["viewport_prefetch"] = {
    "adaptive_distance": True,
    "minimum_telemetry_samples": 4,
    "telemetry_smoothing": 0.35,
    "shrink_hit_rate": 0.20,
    "expand_hit_rate": 0.60,
}
```
