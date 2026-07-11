# Visualization Viewport Prefetch v112

Version 112 adds optional adjacent viewport payload prefetching.

The pipeline can prepare previous and next depth windows in the existing LRU
payload cache. Prefetch does not build scenes or render models, so memory and
CPU use remain bounded while repeated LAS clipping during pan is reduced.

Configuration example:

```python
payload["viewport_prefetch"] = {
    "enabled": True,
    "distance_ratio": 0.75,
    "directions": ["previous", "next"],
}
```

The feature is disabled by default for backward compatibility. Cache metrics
include `prefetches` and `prefetch_skips`.
