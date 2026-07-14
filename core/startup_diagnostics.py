"""Lightweight startup and rerun timing diagnostics.

The registry stores compact primitive records only. It is process-local and is
accessed through ``RuntimeServiceRegistry`` so timers never become part of
serializable application state.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import perf_counter
from typing import Any, Mapping

DEFAULT_STARTUP_BUDGETS_MS: dict[str, float] = {
    "page_config": 100.0,
    "runtime_logging": 150.0,
    "state_controller": 250.0,
    "rerun_begin": 100.0,
    "pending_actions": 300.0,
    "workbench_render": 1200.0,
    "total": 1800.0,
}


@dataclass(frozen=True, slots=True)
class StartupStage:
    name: str
    duration_ms: float
    budget_ms: float | None = None

    @property
    def status(self) -> str:
        if self.budget_ms is None:
            return "measured"
        return "ok" if self.duration_ms <= self.budget_ms else "slow"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": round(float(self.duration_ms), 2),
            "budget_ms": None if self.budget_ms is None else round(float(self.budget_ms), 2),
            "status": self.status,
        }


class StartupDiagnostics:
    """Bounded process-local history of startup/rerun stage timings."""

    def __init__(self, *, max_cycles: int = 30, budgets_ms: Mapping[str, float] | None = None) -> None:
        self._max_cycles = max(1, int(max_cycles))
        self._budgets = dict(DEFAULT_STARTUP_BUDGETS_MS)
        self._budgets.update({str(k): float(v) for k, v in dict(budgets_ms or {}).items()})
        self._cycles: list[dict[str, Any]] = []
        self._lock = RLock()

    def record_cycle(self, stages_ms: Mapping[str, float], *, route_id: str = "", project_id: str = "") -> dict[str, Any]:
        normalized = {str(name): max(0.0, float(value)) for name, value in dict(stages_ms).items()}
        stages = [
            StartupStage(name, duration, self._budgets.get(name)).to_dict()
            for name, duration in normalized.items()
        ]
        slow = [item["name"] for item in stages if item["status"] == "slow"]
        record = {
            "route_id": str(route_id or ""),
            "project_id": str(project_id or ""),
            "stages": stages,
            "total_ms": round(normalized.get("total", sum(normalized.values())), 2),
            "slow_stages": tuple(slow),
            "status": "slow" if slow else "ok",
        }
        with self._lock:
            self._cycles.append(record)
            self._cycles = self._cycles[-self._max_cycles :]
        return dict(record)

    def snapshot(self, *, limit: int = 10) -> dict[str, Any]:
        with self._lock:
            cycles = [dict(item) for item in self._cycles[-max(1, int(limit)) :]]
        latest = cycles[-1] if cycles else {}
        return {
            "latest": latest,
            "cycles": cycles,
            "cycle_count": len(cycles),
            "budgets_ms": dict(self._budgets),
        }


class StartupTimer:
    """Simple stage timer used by the Streamlit application boundary."""

    def __init__(self) -> None:
        self._started = perf_counter()
        self._mark = self._started
        self._stages: dict[str, float] = {}

    def mark(self, name: str) -> float:
        now = perf_counter()
        duration_ms = (now - self._mark) * 1000.0
        self._stages[str(name)] = duration_ms
        self._mark = now
        return duration_ms

    def finish(self) -> dict[str, float]:
        self._stages["total"] = (perf_counter() - self._started) * 1000.0
        return dict(self._stages)
