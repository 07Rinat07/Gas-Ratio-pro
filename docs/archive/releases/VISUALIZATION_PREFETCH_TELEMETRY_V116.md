# Visualization prefetch telemetry v116

Version 116 adds speculative-cache effectiveness telemetry and adaptive neighbor distance.

New cache metrics:
- `prefetch_hits` — prefetched payloads later used by navigation;
- `prefetch_wasted` — unused prefetched payloads removed by eviction or invalidation;
- `prefetch_hit_rate_ppm` — deterministic integer hit-rate metric.

Optional configuration:

```python
payload["viewport_prefetch"] = {
    "adaptive_distance": True,
    "distance_ratio": 0.75,
    "min_distance_ratio": 0.25,
    "max_distance_ratio": 1.25,
}
```

The scheduler expands the neighbor distance when speculative payloads are useful and reduces it when they are mostly wasted. UI code remains free of navigation and performance logic.
