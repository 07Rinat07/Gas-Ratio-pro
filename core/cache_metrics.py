"""Framework-neutral cache telemetry for runtime diagnostics.

The registry stores only primitive counters and bounded cache descriptors. Live
cache values remain owned by their runtime services and are never copied into
serializable application state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CacheMetricSnapshot:
    name: str
    hits: int
    misses: int
    invalidations: int
    evictions: int
    entries: int
    max_entries: int

    @property
    def measured(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return round((self.hits / self.measured) * 100.0, 2) if self.measured else 0.0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["measured"] = self.measured
        payload["hit_rate"] = self.hit_rate
        return payload


class CacheMetricCounter:
    """Mutable runtime counter with a serializable snapshot boundary."""

    def __init__(self, name: str, *, max_entries: int = 0) -> None:
        clean_name = str(name).strip()
        if not clean_name:
            raise ValueError("Cache metric name must not be empty.")
        self.name = clean_name
        self.max_entries = max(0, int(max_entries))
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.evictions = 0
        self.entries = 0

    def hit(self, count: int = 1) -> None:
        self.hits += max(0, int(count))

    def miss(self, count: int = 1) -> None:
        self.misses += max(0, int(count))

    def invalidate(self, count: int = 1) -> None:
        self.invalidations += max(0, int(count))

    def evict(self, count: int = 1) -> None:
        self.evictions += max(0, int(count))

    def set_entries(self, value: int) -> None:
        self.entries = max(0, int(value))

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.evictions = 0
        self.entries = 0

    def snapshot(self) -> CacheMetricSnapshot:
        return CacheMetricSnapshot(
            name=self.name,
            hits=self.hits,
            misses=self.misses,
            invalidations=self.invalidations,
            evictions=self.evictions,
            entries=self.entries,
            max_entries=self.max_entries,
        )


class CacheMetricsRegistry:
    """Runtime registry aggregating cache counters by stable cache name."""

    def __init__(self) -> None:
        self._counters: dict[str, CacheMetricCounter] = {}

    def counter(self, name: str, *, max_entries: int = 0) -> CacheMetricCounter:
        clean_name = str(name).strip()
        if not clean_name:
            raise ValueError("Cache metric name must not be empty.")
        current = self._counters.get(clean_name)
        if current is None:
            current = CacheMetricCounter(clean_name, max_entries=max_entries)
            self._counters[clean_name] = current
        elif max_entries and current.max_entries != int(max_entries):
            current.max_entries = max(0, int(max_entries))
        return current

    def snapshots(self) -> tuple[CacheMetricSnapshot, ...]:
        return tuple(self._counters[name].snapshot() for name in sorted(self._counters))

    def summary(self) -> dict[str, Any]:
        snapshots = self.snapshots()
        hits = sum(item.hits for item in snapshots)
        misses = sum(item.misses for item in snapshots)
        measured = hits + misses
        return {
            "caches": len(snapshots),
            "hits": hits,
            "misses": misses,
            "measured": measured,
            "hit_rate": round((hits / measured) * 100.0, 2) if measured else 0.0,
            "invalidations": sum(item.invalidations for item in snapshots),
            "evictions": sum(item.evictions for item in snapshots),
            "entries": sum(item.entries for item in snapshots),
        }

    def reset(self) -> None:
        for counter in self._counters.values():
            counter.reset()
