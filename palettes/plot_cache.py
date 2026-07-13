from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Hashable, Iterable


@dataclass(frozen=True, slots=True)
class PlotBundle:
    """Immutable bundle of screen figures produced from one presentation snapshot."""

    figures: tuple[Any, ...]
    tablet_figure: Any | None = None


@dataclass(frozen=True, slots=True)
class PlotCacheStats:
    hits: int
    misses: int
    puts: int
    evictions: int
    entries: int
    estimated_bytes: int


class PlotCache:
    """Small observable LRU cache for expensive Plotly bundles.

    The cache stores only a few applied presentation snapshots and exposes
    compact metrics for runtime diagnostics.  Memory is estimated from Plotly
    JSON length without retaining a second serialized copy.
    """

    def __init__(self, *, max_entries: int = 4) -> None:
        if int(max_entries) < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = int(max_entries)
        self._entries: OrderedDict[Hashable, PlotBundle] = OrderedDict()
        self._entry_sizes: dict[Hashable, int] = {}
        self._hits = 0
        self._misses = 0
        self._puts = 0
        self._evictions = 0

    @staticmethod
    def _estimate_figure_bytes(figure: Any) -> int:
        try:
            if hasattr(figure, "to_json"):
                return len(figure.to_json().encode("utf-8"))
            return len(repr(figure).encode("utf-8"))
        except Exception:
            return 0

    @classmethod
    def _estimate_bundle_bytes(cls, bundle: PlotBundle) -> int:
        unique: dict[int, Any] = {}
        for figure in bundle.figures:
            unique[id(figure)] = figure
        if bundle.tablet_figure is not None:
            unique[id(bundle.tablet_figure)] = bundle.tablet_figure
        return sum(cls._estimate_figure_bytes(figure) for figure in unique.values())

    def get(self, key: Hashable) -> PlotBundle | None:
        bundle = self._entries.get(key)
        if bundle is None:
            self._misses += 1
            return None
        self._hits += 1
        self._entries.move_to_end(key)
        return bundle

    def put(self, key: Hashable, figures: Iterable[Any], *, tablet_figure: Any | None = None) -> PlotBundle:
        bundle = PlotBundle(tuple(figures), tablet_figure)
        self._entries[key] = bundle
        self._entry_sizes[key] = self._estimate_bundle_bytes(bundle)
        self._entries.move_to_end(key)
        self._puts += 1
        while len(self._entries) > self.max_entries:
            evicted_key, _ = self._entries.popitem(last=False)
            self._entry_sizes.pop(evicted_key, None)
            self._evictions += 1
        return bundle

    def stats(self) -> PlotCacheStats:
        return PlotCacheStats(
            hits=self._hits,
            misses=self._misses,
            puts=self._puts,
            evictions=self._evictions,
            entries=len(self._entries),
            estimated_bytes=sum(self._entry_sizes.values()),
        )

    def clear(self) -> None:
        self._entries.clear()
        self._entry_sizes.clear()

    def discard_where(self, predicate) -> int:
        removed = 0
        for key in tuple(self._entries):
            if predicate(key):
                self._entries.pop(key, None)
                self._entry_sizes.pop(key, None)
                removed += 1
        return removed

    def __len__(self) -> int:
        return len(self._entries)
