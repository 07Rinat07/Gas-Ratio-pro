"""Bounded runtime cache for expensive dataframe-derived presentation data.

The calculation dataframe is immutable after commit. Streamlit reruns may still
recompute its content hash and screen sample many times. This module reuses
those deterministic derivatives by calculation revision and presentation range.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Hashable

from core.cache_metrics import CacheMetricCounter

import pandas as pd


@dataclass(frozen=True, slots=True)
class DataframeRuntimeStats:
    signature_hits: int
    signature_misses: int
    sample_hits: int
    sample_misses: int
    sample_entries: int
    evictions: int


class DataframeRuntimeCache:
    """Cache one calculation signature and a small set of screen samples."""

    def __init__(self, *, max_samples: int = 8, metrics: CacheMetricCounter | None = None) -> None:
        if max_samples < 1:
            raise ValueError("max_samples must be at least 1")
        self.max_samples = int(max_samples)
        self._signature_key: tuple[Hashable, ...] | None = None
        self._signature_value = ""
        self._samples: OrderedDict[tuple[Hashable, ...], pd.DataFrame] = OrderedDict()
        self._signature_hits = 0
        self._signature_misses = 0
        self._sample_hits = 0
        self._sample_misses = 0
        self._evictions = 0
        self._metrics = metrics
        if self._metrics is not None:
            self._metrics.max_entries = self.max_samples

    @staticmethod
    def frame_identity(frame: pd.DataFrame, revision: int) -> tuple[Hashable, ...]:
        return (
            int(revision),
            id(frame),
            int(len(frame)),
            tuple(str(column) for column in frame.columns),
            tuple(str(dtype) for dtype in frame.dtypes),
        )

    def signature(
        self,
        frame: pd.DataFrame,
        *,
        revision: int,
        builder: Callable[[pd.DataFrame], str],
    ) -> str:
        key = self.frame_identity(frame, revision)
        if self._signature_key == key and self._signature_value:
            self._signature_hits += 1
            if self._metrics is not None:
                self._metrics.hit()
            return self._signature_value
        value = str(builder(frame))
        self._signature_key = key
        self._signature_value = value
        self._signature_misses += 1
        if self._metrics is not None:
            self._metrics.miss()
            if self._samples:
                self._metrics.invalidate(len(self._samples))
        # A new committed calculation invalidates every derived sample.
        self._samples.clear()
        if self._metrics is not None:
            self._metrics.set_entries(0)
        return value

    def screen_sample(
        self,
        frame: pd.DataFrame,
        *,
        source_signature: str,
        depth_range: tuple[float, float],
        max_rows: int,
        sampler: Callable[..., pd.DataFrame],
    ) -> pd.DataFrame:
        key = (
            str(source_signature),
            round(float(depth_range[0]), 6),
            round(float(depth_range[1]), 6),
            int(max_rows),
            int(len(frame)),
        )
        cached = self._samples.get(key)
        if cached is not None:
            self._samples.move_to_end(key)
            self._sample_hits += 1
            if self._metrics is not None:
                self._metrics.hit()
            return cached
        sampled = sampler(frame, max_rows=max_rows)
        self._samples[key] = sampled
        self._samples.move_to_end(key)
        self._sample_misses += 1
        if self._metrics is not None:
            self._metrics.miss()
        while len(self._samples) > self.max_samples:
            self._samples.popitem(last=False)
            self._evictions += 1
            if self._metrics is not None:
                self._metrics.evict()
        if self._metrics is not None:
            self._metrics.set_entries(len(self._samples))
        return sampled

    def clear(self) -> None:
        invalidated = len(self._samples) + (1 if self._signature_value else 0)
        self._signature_key = None
        self._signature_value = ""
        self._samples.clear()
        if self._metrics is not None:
            if invalidated:
                self._metrics.invalidate(invalidated)
            self._metrics.set_entries(0)

    def stats(self) -> DataframeRuntimeStats:
        return DataframeRuntimeStats(
            signature_hits=self._signature_hits,
            signature_misses=self._signature_misses,
            sample_hits=self._sample_hits,
            sample_misses=self._sample_misses,
            sample_entries=len(self._samples),
            evictions=self._evictions,
        )
