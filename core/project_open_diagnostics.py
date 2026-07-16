"""Payload-free profiling for project opening through the Workbench entry boundary.

The profiler records only identifiers, timings and status values. Project
records, repository payloads, DataFrames and Streamlit objects are never kept.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProjectOpenRecord:
    project_id: str
    project_load_ms: float
    recent_project_ms: float
    workspace_open_ms: float
    navigation_ms: float
    total_ms: float
    budget_ms: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_load_ms": round(self.project_load_ms, 2),
            "recent_project_ms": round(self.recent_project_ms, 2),
            "workspace_open_ms": round(self.workspace_open_ms, 2),
            "navigation_ms": round(self.navigation_ms, 2),
            "total_ms": round(self.total_ms, 2),
            "budget_ms": round(self.budget_ms, 2),
            "status": self.status,
        }


class ProjectOpenDiagnostics:
    """Bounded session-local history of project-opening stage timings."""

    def __init__(self, *, max_events: int = 32, budget_ms: float = 750.0) -> None:
        self._events: list[ProjectOpenRecord] = []
        self._max_events = max(1, int(max_events))
        self._budget_ms = max(0.0, float(budget_ms))

    def record(
        self,
        *,
        project_id: str,
        project_load_ms: float,
        recent_project_ms: float,
        workspace_open_ms: float,
        navigation_ms: float,
        total_ms: float,
    ) -> ProjectOpenRecord:
        total = max(0.0, float(total_ms))
        record = ProjectOpenRecord(
            project_id=str(project_id or ""),
            project_load_ms=max(0.0, float(project_load_ms)),
            recent_project_ms=max(0.0, float(recent_project_ms)),
            workspace_open_ms=max(0.0, float(workspace_open_ms)),
            navigation_ms=max(0.0, float(navigation_ms)),
            total_ms=total,
            budget_ms=self._budget_ms,
            status="ok" if total <= self._budget_ms else "slow",
        )
        self._events.append(record)
        if len(self._events) > self._max_events:
            del self._events[:-self._max_events]
        return record

    def snapshot(self, *, limit: int = 20) -> dict[str, Any]:
        events = self._events[-max(1, int(limit)):]
        latest = events[-1].to_dict() if events else {}
        return {
            "budget_ms": round(self._budget_ms, 2),
            "event_count": len(self._events),
            "slow_count": sum(1 for item in self._events if item.status == "slow"),
            "latest": latest,
            "events": [item.to_dict() for item in events],
        }
