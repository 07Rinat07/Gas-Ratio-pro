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
            "source_point_count": self.source_point_count,
            "render_point_count": self.render_point_count,
            "reduction_ratio": self.reduction_ratio,
            "strategy": self.strategy,
            "issues": list(self.issues),
            "contains_raw_dataframe": False,
            "ui_objects_included": False,
        }


class VisualizationRenderModelCache:
    """Small bounded LRU cache for serialized renderer-neutral render models."""

    def __init__(self, capacity: int = 8) -> None:
        self.capacity = max(1, int(capacity))
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        value = self._items.get(key)
        if value is None:
            return None
        self._items.move_to_end(key)
        return json.loads(json.dumps(value, ensure_ascii=False))

    def put(self, key: str, value: Mapping[str, Any]) -> None:
        self._items[key] = json.loads(json.dumps(dict(value), ensure_ascii=False))
        self._items.move_to_end(key)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


class VisualizationPerformanceEngine:
    """Create stable cache keys and performance metadata for one pipeline run."""

    def __init__(self, cache: VisualizationRenderModelCache | None = None) -> None:
        self.cache = cache or VisualizationRenderModelCache()

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

    def store(self, key: str, render_model: Mapping[str, Any]) -> None:
        self.cache.put(key, render_model)

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
            source_points += len(_mapping_list(layer.get("points")))

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

        return VisualizationPerformanceProfile(
            cache_key=key,
            cache_hit=cache_hit,
            cache_enabled=enabled,
            cache_entries=len(self.cache),
            cache_capacity=self.cache.capacity,
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
