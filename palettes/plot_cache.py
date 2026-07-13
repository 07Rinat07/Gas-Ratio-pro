from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Hashable, Iterable


@dataclass(frozen=True, slots=True)
class PlotBundle:
    """Immutable bundle of screen figures produced from one presentation snapshot."""

    figures: tuple[Any, ...]
    tablet_figure: Any | None = None


class PlotCache:
    """Small LRU cache for expensive Plotly bundles.

    The cache deliberately stores only a few applied presentation snapshots. It
    allows users to switch between overview/detail settings without rebuilding
    every figure, while keeping memory bounded for large LAS projects.
    """

    def __init__(self, *, max_entries: int = 4) -> None:
        if int(max_entries) < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = int(max_entries)
        self._entries: OrderedDict[Hashable, PlotBundle] = OrderedDict()

    def get(self, key: Hashable) -> PlotBundle | None:
        bundle = self._entries.get(key)
        if bundle is None:
            return None
        self._entries.move_to_end(key)
        return bundle

    def put(self, key: Hashable, figures: Iterable[Any], *, tablet_figure: Any | None = None) -> PlotBundle:
        bundle = PlotBundle(tuple(figures), tablet_figure)
        self._entries[key] = bundle
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
        return bundle

    def clear(self) -> None:
        self._entries.clear()

    def discard_where(self, predicate) -> int:
        removed = 0
        for key in tuple(self._entries):
            if predicate(key):
                self._entries.pop(key, None)
                removed += 1
        return removed

    def __len__(self) -> int:
        return len(self._entries)
