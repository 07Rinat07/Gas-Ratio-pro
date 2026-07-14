"""Route-scoped lifecycle and timing diagnostics for Modern Workbench.

The tracker stores only compact primitive records.  It coordinates cleanup of
runtime services owned by a previous route and provides measurable budgets for
workspace switches without retaining Streamlit or project payload objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from core.runtime_service_registry import RuntimeServiceRegistry

ROUTE_SCOPE_PREFIX = "route:"
DEFAULT_ROUTE_SWITCH_BUDGET_MS = 750.0
DEFAULT_ROUTE_RENDER_BUDGET_MS = 5000.0


def route_scope(route_id: str) -> str:
    clean = str(route_id or "").strip() or "unknown"
    return f"{ROUTE_SCOPE_PREFIX}{clean}"


@dataclass(frozen=True, slots=True)
class RouteTransitionRecord:
    previous_route: str
    active_route: str
    changed: bool
    cleanup_count: int
    cleanup_failures: int
    transition_ms: float
    budget_ms: float

    @property
    def status(self) -> str:
        if self.cleanup_failures:
            return "error"
        return "ok" if self.transition_ms <= self.budget_ms else "slow"

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_route": self.previous_route,
            "active_route": self.active_route,
            "changed": self.changed,
            "cleanup_count": self.cleanup_count,
            "cleanup_failures": self.cleanup_failures,
            "transition_ms": round(self.transition_ms, 2),
            "budget_ms": round(self.budget_ms, 2),
            "status": self.status,
        }


class WorkbenchRouteLifecycle:
    """Track route changes and dispose only services owned by the old route."""

    def __init__(self, *, max_events: int = 64, switch_budget_ms: float = DEFAULT_ROUTE_SWITCH_BUDGET_MS) -> None:
        self._active_route = ""
        self._events: list[RouteTransitionRecord] = []
        self._max_events = max(1, int(max_events))
        self._switch_budget_ms = max(0.0, float(switch_budget_ms))

    @property
    def active_route(self) -> str:
        return self._active_route

    def activate(self, route_id: str, registry: RuntimeServiceRegistry) -> RouteTransitionRecord:
        started = perf_counter()
        clean = str(route_id or "").strip()
        previous = self._active_route
        changed = bool(previous and clean != previous)
        shutdown = ()
        if changed:
            shutdown = registry.shutdown_scopes({route_scope(previous)}, remove=True)
        self._active_route = clean
        record = RouteTransitionRecord(
            previous_route=previous,
            active_route=clean,
            changed=changed,
            cleanup_count=len(shutdown),
            cleanup_failures=sum(1 for item in shutdown if not item.closed),
            transition_ms=(perf_counter() - started) * 1000.0,
            budget_ms=self._switch_budget_ms,
        )
        self._events.append(record)
        if len(self._events) > self._max_events:
            del self._events[:-self._max_events]
        return record

    def snapshot(self, *, limit: int = 20) -> dict[str, Any]:
        items = self._events[-max(1, int(limit)):]
        changed = [item for item in self._events if item.changed]
        return {
            "active_route": self._active_route,
            "transition_count": len(changed),
            "slow_transition_count": sum(1 for item in changed if item.status == "slow"),
            "cleanup_failures": sum(item.cleanup_failures for item in changed),
            "switch_budget_ms": round(self._switch_budget_ms, 2),
            "events": [item.to_dict() for item in items],
        }
