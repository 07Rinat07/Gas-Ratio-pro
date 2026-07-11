# Visualization Viewport Cache v110

The viewport-aware pipeline now caches prepared payloads by a deterministic
SHA-256 key derived from the source payload and viewport contract.

Repeated requests for the same viewport reuse the clipped/interpolated payload,
while the existing scene pipeline render-model cache reuses final primitives.
The cache is renderer-neutral, bounded by entry count and returns isolated
copies to prevent mutation leaks.

Diagnostics are exposed through the viewport profile and pipeline validation:
`cache_key`, `cache_hit`, `cache_enabled`, and `cache_entries`.
