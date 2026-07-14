from __future__ import annotations

from core.diagnostics_center import build_diagnostics_center_snapshot
from core.runtime_service_registry import RuntimeServiceRegistry, runtime_service_registry
from core.workbench_route_lifecycle import WorkbenchRouteLifecycle, route_scope


class Closable:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_route_change_closes_only_previous_route_services() -> None:
    registry = RuntimeServiceRegistry()
    old = registry.set("old", Closable(), scope=route_scope("nav.data"))
    new = registry.set("new", Closable(), scope=route_scope("nav.correlation"))
    session = registry.set("session", Closable(), scope="session")
    lifecycle = WorkbenchRouteLifecycle()

    lifecycle.activate("nav.data", registry)
    result = lifecycle.activate("nav.correlation", registry)

    assert result.changed is True
    assert result.cleanup_count == 1
    assert old.closed is True
    assert new.closed is False
    assert session.closed is False


def test_same_route_does_not_cleanup_services() -> None:
    registry = RuntimeServiceRegistry()
    service = registry.set("same", Closable(), scope=route_scope("nav.data"))
    lifecycle = WorkbenchRouteLifecycle()

    lifecycle.activate("nav.data", registry)
    result = lifecycle.activate("nav.data", registry)

    assert result.changed is False
    assert result.cleanup_count == 0
    assert service.closed is False


def test_diagnostics_exposes_serializable_route_snapshot() -> None:
    state: dict[str, object] = {}
    registry = runtime_service_registry(state)
    lifecycle = registry.set("workbench_route_lifecycle", WorkbenchRouteLifecycle(), scope="session")
    lifecycle.activate("nav.dashboard", registry)
    lifecycle.activate("nav.data", registry)

    snapshot = build_diagnostics_center_snapshot(state)

    assert snapshot["route_lifecycle"]["active_route"] == "nav.data"
    assert snapshot["route_lifecycle"]["transition_count"] == 1
    assert isinstance(snapshot["route_lifecycle"]["events"], list)
