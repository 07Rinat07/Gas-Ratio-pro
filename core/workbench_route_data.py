"""Lazy route data contracts and compact load diagnostics for Workbench.

Routes declare only the project data they require.  The tracker records
primitive timing metadata and never retains project records, trees, DataFrames
or Streamlit objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Iterable

PROJECT_RECORD = "project_record"
PROJECT_NAVIGATION = "project_navigation"


@dataclass(frozen=True, slots=True)
class RouteDataLoadRecord:
    route_id: str
    project_id: str
    requirements: tuple[str, ...]
    project_ms: float
    navigation_ms: float
    navigation_cache: str
    total_ms: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "project_id": self.project_id,
            "requirements": list(self.requirements),
            "project_ms": round(self.project_ms, 2),
            "navigation_ms": round(self.navigation_ms, 2),
            "navigation_cache": self.navigation_cache,
            "total_ms": round(self.total_ms, 2),
            "status": self.status,
        }


class WorkbenchRouteDataDiagnostics:
    """Bounded process-local history of route data loading costs."""

    def __init__(self, *, max_events: int = 64, budget_ms: float = 1000.0) -> None:
        self._events: list[RouteDataLoadRecord] = []
        self._max_events = max(1, int(max_events))
        self._budget_ms = max(0.0, float(budget_ms))

    def record(
        self,
        *,
        route_id: str,
        project_id: str,
        requirements: Iterable[str],
        project_ms: float,
        navigation_ms: float,
        navigation_cache: str,
        total_ms: float,
    ) -> RouteDataLoadRecord:
        record = RouteDataLoadRecord(
            route_id=str(route_id or ""),
            project_id=str(project_id or ""),
            requirements=tuple(str(item) for item in requirements),
            project_ms=max(0.0, float(project_ms)),
            navigation_ms=max(0.0, float(navigation_ms)),
            navigation_cache=str(navigation_cache or "not-required"),
            total_ms=max(0.0, float(total_ms)),
            status="ok" if float(total_ms) <= self._budget_ms else "slow",
        )
        self._events.append(record)
        if len(self._events) > self._max_events:
            del self._events[:-self._max_events]
        return record

    def snapshot(self, *, limit: int = 20) -> dict[str, Any]:
        events = self._events[-max(1, int(limit)):]
        return {
            "budget_ms": round(self._budget_ms, 2),
            "event_count": len(self._events),
            "slow_count": sum(1 for item in self._events if item.status == "slow"),
            "navigation_cache_hits": sum(1 for item in self._events if item.navigation_cache == "hit"),
            "navigation_cache_misses": sum(1 for item in self._events if item.navigation_cache == "miss"),
            "events": [item.to_dict() for item in events],
        }


class RouteDataTimer:
    """Small helper used by the application boundary while loading route data."""

    def __init__(self) -> None:
        self.started = perf_counter()
        self.project_ms = 0.0
        self.navigation_ms = 0.0

    def measure_project(self, callback):
        started = perf_counter()
        value = callback()
        self.project_ms = (perf_counter() - started) * 1000.0
        return value

    def measure_navigation(self, callback) -> None:
        started = perf_counter()
        callback()
        self.navigation_ms = (perf_counter() - started) * 1000.0

    @property
    def total_ms(self) -> float:
        return (perf_counter() - self.started) * 1000.0
