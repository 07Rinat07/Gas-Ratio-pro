# Visualization Viewport Cache Invalidation v111

This release adds deterministic source and render-configuration fingerprints to the viewport payload cache.

Capabilities:
- automatic cache-key changes when LAS samples or rendering configuration change;
- selective invalidation by source fingerprint;
- selective invalidation by render-configuration fingerprint;
- cache hit, miss, eviction and invalidation metrics;
- renderer-neutral metadata exposed through `viewport_pipeline`.
