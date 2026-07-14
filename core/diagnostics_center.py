"""Serializable diagnostics-center snapshots for Modern Workbench.

The builder reads live runtime services through ``RuntimeServiceRegistry`` but
returns primitives only. It never copies service instances or session values.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.cache_metrics import CacheMetricsRegistry
from core.runtime_diagnostics import RuntimeDiagnostics
from core.runtime_service_registry import RuntimeServiceRegistry, runtime_service_registry
from core.repository_io import RepositoryIOMetrics
from core.operation_tracing import OperationTraceRegistry
from core.session_state_audit import audit_session_state
from core.performance_regression import build_performance_baseline
from core.startup_diagnostics import StartupDiagnostics


@dataclass(frozen=True, slots=True)
class DiagnosticsBudget:
    name: str
    value_ms: float
    budget_ms: float

    @property
    def status(self) -> str:
        return "ok" if self.value_ms <= self.budget_ms else "slow"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value_ms": round(self.value_ms, 2),
            "budget_ms": round(self.budget_ms, 2),
            "status": self.status,
        }


def _runtime_events(service: Any, *, limit: int) -> list[dict[str, Any]]:
    if not isinstance(service, RuntimeDiagnostics):
        return []
    return [item.to_dict() for item in service.snapshot()[-max(1, int(limit)):]]


def _cache_snapshot(service: Any) -> dict[str, Any]:
    if not isinstance(service, CacheMetricsRegistry):
        return {"summary": {}, "caches": []}
    return {
        "summary": dict(service.summary()),
        "caches": [item.to_dict() for item in service.snapshots()],
    }


def _repository_snapshot(service: Any) -> dict[str, Any]:
    if not isinstance(service, RepositoryIOMetrics):
        return {
            "reads": 0, "writes": 0, "deletes": 0, "failures": 0,
            "bytes_read": 0, "bytes_written": 0,
            "total_duration_ms": 0.0, "average_duration_ms": 0.0,
            "events": [],
        }
    return service.snapshot().to_dict()



def _startup_snapshot(service: Any, *, limit: int) -> dict[str, Any]:
    if not isinstance(service, StartupDiagnostics):
        return {"latest": {}, "cycles": [], "cycle_count": 0, "budgets_ms": {}}
    return service.snapshot(limit=limit)


def _trace_snapshot(service: Any, *, limit: int) -> dict[str, Any]:
    if not isinstance(service, OperationTraceRegistry):
        return {"summary": {}, "events": []}
    return {
        "summary": dict(service.summary()),
        "events": [item.to_dict() for item in service.snapshot(limit=limit)],
    }

def _budget_snapshot(events: list[dict[str, Any]], budgets: Mapping[str, float]) -> list[dict[str, Any]]:
    latest: dict[str, float] = {}
    for event in events:
        stage = str(event.get("stage") or "")
        if stage in budgets:
            latest[stage] = float(event.get("duration_ms") or 0.0)
    return [
        DiagnosticsBudget(stage, latest[stage], float(budget)).to_dict()
        for stage, budget in budgets.items()
        if stage in latest
    ]


def build_diagnostics_center_snapshot(
    state: Mapping[str, Any],
    *,
    event_limit: int = 20,
    performance_budgets_ms: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Return a compact, JSON-compatible diagnostics snapshot."""

    # ``runtime_service_registry`` needs a mutable mapping only when it has to
    # repair legacy state. Normal Workbench state is mutable; tests may pass an
    # immutable mapping, in which case diagnostics remain available without a
    # registry repair side effect.
    if isinstance(state, dict):
        registry = runtime_service_registry(state)
    else:
        current = state.get("runtime::services")
        registry = current if isinstance(current, RuntimeServiceRegistry) else RuntimeServiceRegistry()

    runtime_service = registry.get("runtime_diagnostics")
    events = _runtime_events(runtime_service, limit=event_limit)
    cache = _cache_snapshot(registry.get("cache_metrics_registry"))
    repository = _repository_snapshot(registry.get("repository_io_metrics"))
    traces = _trace_snapshot(registry.get("operation_trace_registry"), limit=event_limit)
    startup = _startup_snapshot(registry.get("startup_diagnostics"), limit=event_limit)
    session = audit_session_state(state).to_dict()
    descriptors = [
        {"key": item.key, "type_name": item.type_name}
        for item in registry.descriptors()
    ]
    budgets = dict(performance_budgets_ms or {})

    snapshot = {
        "runtime": {
            "registry": registry.snapshot().to_dict(),
            "services": descriptors,
            "service_scopes": {item.key: item.scope for item in registry.descriptors()},
            "events": events,
            "event_count": len(events),
        },
        "cache": cache,
        "repository": repository,
        "traces": traces,
        "startup": startup,
        "session": session,
        "budgets": _budget_snapshot(events, budgets),
    }
    snapshot["performance_baseline"] = build_performance_baseline(snapshot).to_dict()
    return snapshot
