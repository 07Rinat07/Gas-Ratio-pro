"""Bounded runtime cache for expensive LAS correlation render artifacts.

The cache is a runtime service: Plotly figures and panel objects never enter the
serializable application state.  Entries use LRU eviction and expose only
primitive telemetry through ``CacheMetricCounter``.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Hashable

from core.cache_metrics import CacheMetricCounter


@dataclass(frozen=True, slots=True)
class CorrelationRenderArtifacts:
    studio_panel: Any
    studio_figure: Any
    figure: Any
    figure_title: str
    figure_file_name: str


class CorrelationRuntimeCache:
    """Small LRU cache for correlation render artifacts."""

    def __init__(self, *, max_entries: int = 3, metrics: CacheMetricCounter | None = None) -> None:
        if int(max_entries) < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = int(max_entries)
        self._entries: OrderedDict[Hashable, CorrelationRenderArtifacts] = OrderedDict()
        self._metrics = metrics
        self._sync_metrics()

    def get(self, key: Hashable) -> CorrelationRenderArtifacts | None:
        value = self._entries.get(key)
        if value is None:
            if self._metrics is not None:
                self._metrics.miss()
            return None
        self._entries.move_to_end(key)
        if self._metrics is not None:
            self._metrics.hit()
        return value

    def put(self, key: Hashable, value: CorrelationRenderArtifacts) -> None:
        if key in self._entries:
            self._entries.pop(key)
        self._entries[key] = value
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
            if self._metrics is not None:
                self._metrics.evict()
        self._sync_metrics()

    def invalidate(self, key: Hashable | None = None) -> int:
        if key is None:
            removed = len(self._entries)
            self._entries.clear()
        else:
            removed = 1 if self._entries.pop(key, None) is not None else 0
        if removed and self._metrics is not None:
            self._metrics.invalidate(removed)
        self._sync_metrics()
        return removed

    def clear(self) -> int:
        return self.invalidate()

    def __len__(self) -> int:
        return len(self._entries)

    def _sync_metrics(self) -> None:
        if self._metrics is not None:
            self._metrics.max_entries = self.max_entries
            self._metrics.set_entries(len(self._entries))
