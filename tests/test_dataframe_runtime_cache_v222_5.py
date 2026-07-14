from __future__ import annotations

import pandas as pd

from core.dataframe_runtime_cache import DataframeRuntimeCache
from core.presentation_runtime import dataframe_signature
from palettes.plot_engine import downsample_frame_for_screen


def _frame(rows: int = 5000) -> pd.DataFrame:
    return pd.DataFrame({"depth": range(rows), "c1": range(rows)})


def test_signature_is_computed_once_per_committed_revision() -> None:
    frame = _frame(20)
    cache = DataframeRuntimeCache()
    calls = 0

    def builder(value: pd.DataFrame) -> str:
        nonlocal calls
        calls += 1
        return dataframe_signature(value)

    first = cache.signature(frame, revision=3, builder=builder)
    second = cache.signature(frame, revision=3, builder=builder)

    assert first == second
    assert calls == 1
    assert cache.stats().signature_hits == 1
    assert cache.stats().signature_misses == 1


def test_revision_change_invalidates_signature_and_samples() -> None:
    frame = _frame()
    cache = DataframeRuntimeCache()
    sig1 = cache.signature(frame, revision=1, builder=dataframe_signature)
    cache.screen_sample(
        frame,
        source_signature=sig1,
        depth_range=(0.0, 4999.0),
        max_rows=100,
        sampler=downsample_frame_for_screen,
    )
    assert cache.stats().sample_entries == 1

    cache.signature(frame, revision=2, builder=dataframe_signature)
    assert cache.stats().sample_entries == 0


def test_screen_sample_is_reused_for_same_range() -> None:
    frame = _frame()
    cache = DataframeRuntimeCache(max_samples=2)
    signature = cache.signature(frame, revision=1, builder=dataframe_signature)

    first = cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(0.0, 4999.0),
        max_rows=200,
        sampler=downsample_frame_for_screen,
    )
    second = cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(0.0, 4999.0),
        max_rows=200,
        sampler=downsample_frame_for_screen,
    )

    assert first is second
    assert len(first) <= 202
    assert cache.stats().sample_hits == 1
    assert cache.stats().sample_misses == 1


def test_sample_cache_is_bounded() -> None:
    frame = _frame()
    cache = DataframeRuntimeCache(max_samples=2)
    signature = cache.signature(frame, revision=1, builder=dataframe_signature)
    for index in range(3):
        cache.screen_sample(
            frame.iloc[index * 100 :],
            source_signature=signature,
            depth_range=(float(index), 4999.0),
            max_rows=100,
            sampler=downsample_frame_for_screen,
        )
    stats = cache.stats()
    assert stats.sample_entries == 2
    assert stats.evictions == 1


def test_dataframe_runtime_cache_updates_shared_metrics() -> None:
    from core.cache_metrics import CacheMetricsRegistry

    registry = CacheMetricsRegistry()
    counter = registry.counter("dataframe", max_entries=2)
    cache = DataframeRuntimeCache(max_samples=2, metrics=counter)
    frame = pd.DataFrame({"DEPTH": [1.0, 2.0, 3.0], "VALUE": [4.0, 5.0, 6.0]})

    signature = cache.signature(frame, revision=1, builder=lambda _: "sig")
    cache.signature(frame, revision=1, builder=lambda _: "unused")
    cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(1.0, 3.0),
        max_rows=2,
        sampler=lambda source, max_rows: source.head(max_rows),
    )
    cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(1.0, 3.0),
        max_rows=2,
        sampler=lambda source, max_rows: source.head(max_rows),
    )

    snapshot = counter.snapshot()
    assert snapshot.hits == 2
    assert snapshot.misses == 2
    assert snapshot.entries == 1
    assert snapshot.hit_rate == 50.0

    cache.clear()
    assert counter.snapshot().invalidations == 2
    assert counter.snapshot().entries == 0


def test_sample_cache_evicts_by_memory_budget() -> None:
    frame = pd.DataFrame({"value": ["x" * 100 for _ in range(20)]})
    probe = frame.head(10).copy()
    sample_bytes = DataframeRuntimeCache.estimate_frame_bytes(probe)
    cache = DataframeRuntimeCache(max_samples=8, max_bytes=sample_bytes + 32)
    signature = cache.signature(frame, revision=1, builder=lambda _: "sig")

    cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(0.0, 9.0),
        max_rows=10,
        sampler=lambda source, max_rows: source.head(max_rows).copy(),
    )
    cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(10.0, 19.0),
        max_rows=10,
        sampler=lambda source, max_rows: source.tail(max_rows).copy(),
    )

    stats = cache.stats()
    assert stats.sample_entries == 1
    assert stats.evictions == 1
    assert stats.sample_bytes <= stats.max_sample_bytes


def test_oversized_sample_is_returned_but_not_cached() -> None:
    frame = pd.DataFrame({"value": ["x" * 1000 for _ in range(10)]})
    cache = DataframeRuntimeCache(max_samples=4, max_bytes=128)
    signature = cache.signature(frame, revision=1, builder=lambda _: "sig")

    result = cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(0.0, 9.0),
        max_rows=10,
        sampler=lambda source, max_rows: source.head(max_rows).copy(),
    )

    assert len(result) == 10
    stats = cache.stats()
    assert stats.sample_entries == 0
    assert stats.oversized_skips == 1
    assert stats.sample_bytes == 0


def test_close_releases_cached_dataframe_memory() -> None:
    frame = _frame(100)
    cache = DataframeRuntimeCache(max_bytes=1024 * 1024)
    signature = cache.signature(frame, revision=1, builder=lambda _: "sig")
    cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(0.0, 99.0),
        max_rows=50,
        sampler=lambda source, max_rows: source.head(max_rows).copy(),
    )
    assert cache.stats().sample_bytes > 0

    cache.close()

    assert cache.stats().sample_entries == 0
    assert cache.stats().sample_bytes == 0
