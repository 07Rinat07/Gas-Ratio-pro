from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Hashable, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class PlotBundle:
    """Immutable figures and pre-serialized screen payloads for one snapshot.

    ``screen_payloads`` are prepared once when the bundle enters the cache.  On
    subsequent Streamlit reruns the UI can pass dictionaries directly to
    ``st.plotly_chart`` and avoid repeating Plotly's expensive figure-to-JSON
    conversion for unchanged figures.
    """

    figures: tuple[Any, ...]
    screen_payloads: tuple[Mapping[str, Any], ...]
    fingerprints: tuple[str, ...]
    tablet_figure: Any | None = None
    serialized_bytes: int = 0


@dataclass(frozen=True, slots=True)
class PlotCacheStats:
    hits: int
    misses: int
    puts: int
    evictions: int
    entries: int
    estimated_bytes: int
    serialized_figures: int


class PlotCache:
    """Small observable LRU cache for expensive Plotly bundles.

    Besides retaining the original figures for report/export workflows, the
    cache stores normalized dictionaries for browser rendering.  Serialization
    therefore happens once per cache miss rather than on every Streamlit rerun.
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
        self._serialized_figures = 0

    @staticmethod
    def _serialize_figure(figure: Any) -> tuple[Mapping[str, Any], str, int]:
        """Return a JSON-compatible payload, stable fingerprint and byte size."""

        try:
            if hasattr(figure, "to_json"):
                raw = figure.to_json()
                payload = json.loads(raw)
            elif isinstance(figure, Mapping):
                payload = dict(figure)
                raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
            else:
                payload = {"data": [], "layout": {}}
                raw = json.dumps(payload, separators=(",", ":"))
        except Exception:
            payload = {"data": [], "layout": {}}
            raw = json.dumps(payload, separators=(",", ":"))
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
        return payload, digest, len(raw.encode("utf-8"))

    @classmethod
    def _build_bundle(cls, figures: Iterable[Any], tablet_figure: Any | None = None) -> PlotBundle:
        figure_tuple = tuple(figures)
        payloads: list[Mapping[str, Any]] = []
        fingerprints: list[str] = []
        total_bytes = 0
        for figure in figure_tuple:
            payload, fingerprint, size = cls._serialize_figure(figure)
            payloads.append(payload)
            fingerprints.append(fingerprint)
            total_bytes += size
        # The tablet can already be present in ``figures``.  Count only an
        # additional unique object to keep memory diagnostics meaningful.
        if tablet_figure is not None and all(id(tablet_figure) != id(item) for item in figure_tuple):
            _, _, tablet_size = cls._serialize_figure(tablet_figure)
            total_bytes += tablet_size
        return PlotBundle(
            figures=figure_tuple,
            screen_payloads=tuple(payloads),
            fingerprints=tuple(fingerprints),
            tablet_figure=tablet_figure,
            serialized_bytes=total_bytes,
        )

    def get(self, key: Hashable) -> PlotBundle | None:
        bundle = self._entries.get(key)
        if bundle is None:
            self._misses += 1
            return None
        self._hits += 1
        self._entries.move_to_end(key)
        return bundle

    def put(self, key: Hashable, figures: Iterable[Any], *, tablet_figure: Any | None = None) -> PlotBundle:
        bundle = self._build_bundle(figures, tablet_figure)
        self._entries[key] = bundle
        self._entry_sizes[key] = bundle.serialized_bytes
        self._entries.move_to_end(key)
        self._puts += 1
        self._serialized_figures += len(bundle.screen_payloads)
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
            serialized_figures=self._serialized_figures,
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
