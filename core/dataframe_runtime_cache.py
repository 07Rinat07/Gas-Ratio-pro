"""Memory-bounded runtime cache for dataframe-derived presentation data.

The calculation dataframe is immutable after commit. Streamlit reruns may still
recompute its content hash and screen samples many times. This cache reuses those
deterministic derivatives without placing DataFrame objects in Session State.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Hashable

import pandas as pd

from core.cache_metrics import CacheMetricCounter

DEFAULT_DATAFRAME_CACHE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DataframeRuntimeStats:
    signature_hits: int
    signature_misses: int
    sample_hits: int
    sample_misses: int
    sample_entries: int
    evictions: int
    sample_bytes: int
    peak_sample_bytes: int
    max_sample_bytes: int
    oversized_skips: int

    @property
    def memory_utilization_percent(self) -> float:
        if self.max_sample_bytes <= 0:
            return 0.0
        return round((self.sample_bytes / self.max_sample_bytes) * 100.0, 2)

    def to_dict(self) -> dict[str, int | float]:
        return {
            "signature_hits": self.signature_hits,
            "signature_misses": self.signature_misses,
            "sample_hits": self.sample_hits,
            "sample_misses": self.sample_misses,
            "sample_entries": self.sample_entries,
            "evictions": self.evictions,
            "sample_bytes": self.sample_bytes,
            "peak_sample_bytes": self.peak_sample_bytes,
            "max_sample_bytes": self.max_sample_bytes,
            "oversized_skips": self.oversized_skips,
            "memory_utilization_percent": self.memory_utilization_percent,
        }


class DataframeRuntimeCache:
    """Cache one calculation signature and memory-bounded screen samples."""

    def __init__(
        self,
        *,
        max_samples: int = 8,
        max_bytes: int = DEFAULT_DATAFRAME_CACHE_BYTES,
        metrics: CacheMetricCounter | None = None,
    ) -> None:
        if max_samples < 1:
            raise ValueError("max_samples must be at least 1")
        if max_bytes < 1:
            raise ValueError("max_bytes must be at least 1")
        self.max_samples = int(max_samples)
        self.max_bytes = int(max_bytes)
        self._signature_key: tuple[Hashable, ...] | None = None
        self._signature_value = ""
        self._samples: OrderedDict[tuple[Hashable, ...], pd.DataFrame] = OrderedDict()
        self._sample_sizes: dict[tuple[Hashable, ...], int] = {}
        self._sample_bytes = 0
        self._peak_sample_bytes = 0
        self._signature_hits = 0
        self._signature_misses = 0
        self._sample_hits = 0
        self._sample_misses = 0
        self._evictions = 0
        self._oversized_skips = 0
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

    @staticmethod
    def estimate_frame_bytes(frame: pd.DataFrame) -> int:
        """Return deep DataFrame memory usage without copying frame contents."""

        try:
            return max(0, int(frame.memory_usage(index=True, deep=True).sum()))
        except Exception:
            # Diagnostics must never make presentation unavailable.
            return max(0, int(getattr(frame, "__sizeof__", lambda: 0)()))

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
        self._clear_samples()
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
        sample_bytes = self.estimate_frame_bytes(sampled)
        self._sample_misses += 1
        if self._metrics is not None:
            self._metrics.miss()

        # A single oversize sample is returned but not retained, keeping the
        # runtime budget strict and predictable.
        if sample_bytes > self.max_bytes:
            self._oversized_skips += 1
            return sampled

        self._samples[key] = sampled
        self._sample_sizes[key] = sample_bytes
        self._sample_bytes += sample_bytes
        self._peak_sample_bytes = max(self._peak_sample_bytes, self._sample_bytes)
        self._samples.move_to_end(key)
        self._evict_to_budget()
        if self._metrics is not None:
            self._metrics.set_entries(len(self._samples))
        return sampled

    def _evict_to_budget(self) -> None:
        while self._samples and (
            len(self._samples) > self.max_samples or self._sample_bytes > self.max_bytes
        ):
            key, _frame = self._samples.popitem(last=False)
            self._sample_bytes = max(0, self._sample_bytes - self._sample_sizes.pop(key, 0))
            self._evictions += 1
            if self._metrics is not None:
                self._metrics.evict()

    def _clear_samples(self) -> None:
        self._samples.clear()
        self._sample_sizes.clear()
        self._sample_bytes = 0
        if self._metrics is not None:
            self._metrics.set_entries(0)

    def clear(self) -> None:
        invalidated = len(self._samples) + (1 if self._signature_value else 0)
        self._signature_key = None
        self._signature_value = ""
        self._clear_samples()
        if self._metrics is not None and invalidated:
            self._metrics.invalidate(invalidated)

    def close(self) -> None:
        """Lifecycle hook used by project-scoped runtime cleanup."""

        self.clear()

    def stats(self) -> DataframeRuntimeStats:
        return DataframeRuntimeStats(
            signature_hits=self._signature_hits,
            signature_misses=self._signature_misses,
            sample_hits=self._sample_hits,
            sample_misses=self._sample_misses,
            sample_entries=len(self._samples),
            evictions=self._evictions,
            sample_bytes=self._sample_bytes,
            peak_sample_bytes=self._peak_sample_bytes,
            max_sample_bytes=self.max_bytes,
            oversized_skips=self._oversized_skips,
        )
