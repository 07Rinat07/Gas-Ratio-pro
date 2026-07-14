from core.cache_metrics import CacheMetricsRegistry


def test_cache_metrics_registry_aggregates_hits_misses_and_invalidations() -> None:
    registry = CacheMetricsRegistry()
    dataframe = registry.counter("dataframe", max_entries=8)
    figure = registry.counter("figure", max_entries=4)

    dataframe.hit(3)
    dataframe.miss(1)
    dataframe.invalidate(2)
    dataframe.set_entries(5)
    figure.hit(1)
    figure.miss(1)
    figure.evict(1)
    figure.set_entries(3)

    summary = registry.summary()

    assert summary == {
        "caches": 2,
        "hits": 4,
        "misses": 2,
        "measured": 6,
        "hit_rate": 66.67,
        "invalidations": 2,
        "evictions": 1,
        "entries": 8,
    }
    snapshots = {item.name: item for item in registry.snapshots()}
    assert snapshots["dataframe"].max_entries == 8
    assert snapshots["figure"].hit_rate == 50.0


def test_cache_metrics_reset_preserves_registered_caches() -> None:
    registry = CacheMetricsRegistry()
    counter = registry.counter("runtime")
    counter.hit()
    counter.set_entries(2)

    registry.reset()

    assert registry.summary()["caches"] == 1
    assert registry.summary()["measured"] == 0
    assert registry.snapshots()[0].entries == 0
