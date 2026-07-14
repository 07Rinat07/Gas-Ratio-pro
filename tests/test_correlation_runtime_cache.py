from core.cache_metrics import CacheMetricCounter
from core.correlation_runtime_cache import CorrelationRenderArtifacts, CorrelationRuntimeCache


def artifact(name: str) -> CorrelationRenderArtifacts:
    return CorrelationRenderArtifacts(name, None, name, f"title-{name}", f"file-{name}")


def test_lru_cache_tracks_hits_misses_and_evictions() -> None:
    metrics = CacheMetricCounter("correlation", max_entries=2)
    cache = CorrelationRuntimeCache(max_entries=2, metrics=metrics)

    cache.put("a", artifact("a"))
    cache.put("b", artifact("b"))
    assert cache.get("a").figure == "a"
    assert cache.get("missing") is None

    cache.put("c", artifact("c"))
    assert cache.get("b") is None
    snapshot = metrics.snapshot()
    assert snapshot.hits == 1
    assert snapshot.misses == 2
    assert snapshot.evictions == 1
    assert snapshot.entries == 2


def test_invalidate_clears_runtime_artifacts_without_serializing_them() -> None:
    metrics = CacheMetricCounter("correlation", max_entries=3)
    cache = CorrelationRuntimeCache(max_entries=3, metrics=metrics)
    cache.put(("well", 1), artifact("one"))
    cache.put(("well", 2), artifact("two"))

    assert cache.invalidate(("well", 1)) == 1
    assert len(cache) == 1
    assert cache.clear() == 1
    assert len(cache) == 0
    assert metrics.snapshot().invalidations == 2
