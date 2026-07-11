"""Performance support for the renderer-neutral visualization pipeline.

The module provides a deterministic render-model cache key, a bounded in-memory
LRU cache and serializable performance metadata.  It deliberately does not
contain UI logic and never stores raw DataFrame objects.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class VisualizationPerformanceProfile:
    schema: str = "visualization.performance.profile"
    version: str = "1.0"
    cache_key: str = ""
    cache_hit: bool = False
    cache_enabled: bool = True
    cache_entries: int = 0
    cache_capacity: int = 0
    cache_bytes: int = 0
    cache_max_bytes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_evictions: int = 0
    cache_rejections: int = 0
    source_point_count: int = 0
    render_point_count: int = 0
    reduction_ratio: float = 0.0
    strategy: str = "reuse_render_model"
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.cache_key) and not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "ok": self.ok,
            "cache_key": self.cache_key,
            "cache_hit": self.cache_hit,
            "cache_enabled": self.cache_enabled,
            "cache_entries": self.cache_entries,
            "cache_capacity": self.cache_capacity,
            "cache_bytes": self.cache_bytes,
            "cache_max_bytes": self.cache_max_bytes,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_evictions": self.cache_evictions,
            "cache_rejections": self.cache_rejections,
            "source_point_count": self.source_point_count,
            "render_point_count": self.render_point_count,
            "reduction_ratio": self.reduction_ratio,
            "strategy": self.strategy,
            "issues": list(self.issues),
            "contains_raw_dataframe": False,
            "ui_objects_included": False,
        }


class VisualizationRenderModelCache:
    """Bounded LRU cache constrained by entry count and serialized byte size.

    Render models are copied through JSON serialization before storage.  This
    keeps the cache renderer-neutral, prevents accidental mutation and gives a
    deterministic byte estimate without retaining raw DataFrame objects.
    """

    def __init__(self, capacity: int = 8, max_bytes: int = 8 * 1024 * 1024) -> None:
        self.capacity = max(1, int(capacity))
        self.max_bytes = max(1, int(max_bytes))
        self._items: OrderedDict[str, tuple[dict[str, Any], int]] = OrderedDict()
        self._current_bytes = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.rejections = 0

    @staticmethod
    def _serialize(value: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
        encoded = json.dumps(dict(value), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return json.loads(encoded.decode("utf-8")), len(encoded)

    @property
    def current_bytes(self) -> int:
        return self._current_bytes

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._items.get(key)
        if entry is None:
            self.misses += 1
            return None
        self.hits += 1
        self._items.move_to_end(key)
        value, _size = entry
        return json.loads(json.dumps(value, ensure_ascii=False))

    def put(self, key: str, value: Mapping[str, Any]) -> bool:
        prepared, size = self._serialize(value)
        previous = self._items.pop(key, None)
        if previous is not None:
            self._current_bytes -= previous[1]

        if size > self.max_bytes:
            self.rejections += 1
            return False

        self._items[key] = (prepared, size)
        self._current_bytes += size
        self._items.move_to_end(key)
        while len(self._items) > self.capacity or self._current_bytes > self.max_bytes:
            _evicted_key, (_evicted_value, evicted_size) = self._items.popitem(last=False)
            self._current_bytes -= evicted_size
            self.evictions += 1
        return True

    def invalidate(self, key: str) -> bool:
        """Remove one cached render model without clearing unrelated entries."""
        entry = self._items.pop(key, None)
        if entry is None:
            return False
        self._current_bytes -= entry[1]
        return True

    def clear(self) -> None:
        self._items.clear()
        self._current_bytes = 0

    def stats(self) -> dict[str, int]:
        return {
            "entries": len(self._items),
            "capacity": self.capacity,
            "bytes": self._current_bytes,
            "max_bytes": self.max_bytes,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "rejections": self.rejections,
        }

    def __len__(self) -> int:
        return len(self._items)


class VisualizationPerformanceEngine:
    """Create stable cache keys and performance metadata for one pipeline run."""

    def __init__(self, cache: VisualizationRenderModelCache | None = None) -> None:
        self.cache = cache if cache is not None else VisualizationRenderModelCache()

    def cache_key(self, *contracts: Mapping[str, Any]) -> str:
        canonical = json.dumps(
            [dict(contract) for contract in contracts],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return sha256(canonical).hexdigest()

    def lookup(self, key: str) -> dict[str, Any] | None:
        return self.cache.get(key)

    def store(self, key: str, render_model: Mapping[str, Any]) -> bool:
        return self.cache.put(key, render_model)

    def invalidate(self, key: str) -> bool:
        """Invalidate exactly one geometry contract."""
        return self.cache.invalidate(key)

    def invalidate_contracts(self, *contracts: Mapping[str, Any]) -> bool:
        """Invalidate the cache entry produced by the supplied contracts."""
        return self.invalidate(self.cache_key(*contracts))

    def profile(
        self,
        *,
        key: str,
        cache_hit: bool,
        scene: Mapping[str, Any],
        render_model: Mapping[str, Any],
        enabled: bool = True,
    ) -> VisualizationPerformanceProfile:
        source_points = 0
        for layer in _mapping_list(scene.get("layers")):
            payload = layer.get("payload") if isinstance(layer.get("payload"), Mapping) else {}
            source_points += len(_mapping_list(payload.get("points")))

        render_points = 0
        for primitive in _mapping_list(render_model.get("primitives")):
            if str(primitive.get("kind") or "") == "polyline":
                payload = primitive.get("payload") if isinstance(primitive.get("payload"), Mapping) else {}
                render_points += len(_mapping_list(payload.get("points")))

        reduction = 0.0
        if source_points > 0:
            reduction = max(0.0, min(1.0, 1.0 - (render_points / source_points)))

        issues: list[str] = []
        if not key:
            issues.append("visualization_performance_cache_key_missing")

        cache_stats = self.cache.stats()
        return VisualizationPerformanceProfile(
            cache_key=key,
            cache_hit=cache_hit,
            cache_enabled=enabled,
            cache_entries=cache_stats["entries"],
            cache_capacity=cache_stats["capacity"],
            cache_bytes=cache_stats["bytes"],
            cache_max_bytes=cache_stats["max_bytes"],
            cache_hits=cache_stats["hits"],
            cache_misses=cache_stats["misses"],
            cache_evictions=cache_stats["evictions"],
            cache_rejections=cache_stats["rejections"],
            source_point_count=source_points,
            render_point_count=render_points,
            reduction_ratio=round(reduction, 6),
            issues=tuple(issues),
        )


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


__all__ = [
    "VisualizationPerformanceEngine",
    "VisualizationPerformanceProfile",
    "VisualizationRenderModelCache",
]
