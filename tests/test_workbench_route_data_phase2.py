from __future__ import annotations

from core.diagnostics_center import build_diagnostics_center_snapshot
from core.lazy_workspace import LazyWorkspaceRegistry, WorkspaceRoute
from core.runtime_service_registry import runtime_service_registry
from core.workbench_route_data import (
    PROJECT_NAVIGATION,
    PROJECT_RECORD,
    WorkbenchRouteDataDiagnostics,
)


def test_workspace_route_declares_data_requirements_without_resolving_other_routes() -> None:
    called: list[str] = []
    registry = LazyWorkspaceRegistry({
        "nav.data": WorkspaceRoute(
            "nav.data", "data", lambda project: called.append(str(project)),
            data_requirements=(PROJECT_RECORD, PROJECT_NAVIGATION),
        ),
        "nav.docs": WorkspaceRoute(
            "nav.docs", "docs", lambda project: called.append("docs"),
            data_requirements=(),
        ),
    })

    route = registry.resolve("nav.docs")

    assert route is not None
    assert route.data_requirements == ()
    assert called == []


def test_route_data_diagnostics_are_bounded_and_serializable() -> None:
    diagnostics = WorkbenchRouteDataDiagnostics(max_events=2, budget_ms=10.0)
    diagnostics.record(
        route_id="nav.data", project_id="p1",
        requirements=(PROJECT_RECORD, PROJECT_NAVIGATION),
        project_ms=1.0, navigation_ms=2.0, navigation_cache="miss", total_ms=3.0,
    )
    diagnostics.record(
        route_id="nav.correlation", project_id="p1",
        requirements=(PROJECT_RECORD, PROJECT_NAVIGATION),
        project_ms=1.0, navigation_ms=0.0, navigation_cache="hit", total_ms=4.0,
    )
    diagnostics.record(
        route_id="nav.docs", project_id="",
        requirements=(), project_ms=0.0, navigation_ms=0.0,
        navigation_cache="not-required", total_ms=12.0,
    )

    snapshot = diagnostics.snapshot(limit=10)

    assert snapshot["event_count"] == 2
    assert snapshot["slow_count"] == 1
    assert snapshot["navigation_cache_hits"] == 1
    assert snapshot["navigation_cache_misses"] == 0
    assert snapshot["events"][0]["route_id"] == "nav.correlation"
    assert snapshot["events"][1]["requirements"] == []


def test_diagnostics_center_exposes_route_data_loading_snapshot() -> None:
    state: dict[str, object] = {}
    registry = runtime_service_registry(state)
    diagnostics = registry.set(
        "workbench_route_data_diagnostics",
        WorkbenchRouteDataDiagnostics(),
        scope="session",
    )
    diagnostics.record(
        route_id="nav.data", project_id="project-a",
        requirements=(PROJECT_RECORD, PROJECT_NAVIGATION),
        project_ms=2.0, navigation_ms=5.0, navigation_cache="miss", total_ms=7.0,
    )

    snapshot = build_diagnostics_center_snapshot(state)

    assert snapshot["route_data"]["event_count"] == 1
    assert snapshot["route_data"]["navigation_cache_misses"] == 1
    assert snapshot["route_data"]["events"][0]["project_id"] == "project-a"
