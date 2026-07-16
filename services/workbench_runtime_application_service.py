"""Session-scoped runtime coordination boundary for Modern Workbench.

The Streamlit layer must not access :class:`RuntimeServiceRegistry` directly.
This application service owns route lifecycle, startup diagnostics, and
cross-cache invalidation while exposing only explicit, lightweight use cases.
"""

from __future__ import annotations

from typing import Any, Mapping

from core.runtime_service_registry import RuntimeServiceRegistry
from core.startup_diagnostics import StartupDiagnostics
from core.workbench_route_lifecycle import RouteTransitionRecord, WorkbenchRouteLifecycle
from core.workbench_route_data import WorkbenchRouteDataDiagnostics


class WorkbenchRuntimeApplicationService:
    """Coordinate process-local Workbench runtime infrastructure."""

    def __init__(self, *, registry: RuntimeServiceRegistry) -> None:
        self._registry = registry

    def activate_route(self, route_id: str) -> RouteTransitionRecord:
        """Activate a route and dispose runtime services owned by the old route."""
        lifecycle = self._registry.ensure(
            "workbench_route_lifecycle",
            WorkbenchRouteLifecycle,
            expected_type=WorkbenchRouteLifecycle,
            scope="session",
        )
        return lifecycle.activate(str(route_id or ""), self._registry)

    def record_startup_cycle(
        self,
        stages_ms: Mapping[str, float],
        *,
        route_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        """Record one bounded startup/rerun timing cycle."""
        diagnostics = self._registry.ensure(
            "startup_diagnostics",
            StartupDiagnostics,
            expected_type=StartupDiagnostics,
            scope="session",
        )
        return diagnostics.record_cycle(
            stages_ms,
            route_id=str(route_id or ""),
            project_id=str(project_id or ""),
        )

    def invalidate_project_runtime_caches(
        self,
        project_id: str,
        *,
        active_project_id: str = "",
        reason: str = "repository-mutation",
    ) -> dict[str, bool]:
        """Invalidate known runtime caches after a project mutation.

        Navigation data is project-addressable and is always invalidated. The
        DataFrame cache is cleared only when the changed project is currently
        active, preventing unrelated project mutations from discarding the
        active analytical working set.
        """
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            return {"navigation": False, "dataframe": False}

        navigation_invalidated = False
        navigation_cache = self._registry.get("project_navigation_runtime_cache")
        invalidate = getattr(navigation_cache, "invalidate", None)
        if callable(invalidate):
            invalidate(clean_project_id, reason=str(reason or "repository-mutation"))
            navigation_invalidated = True

        dataframe_cleared = False
        if str(active_project_id or "").strip() == clean_project_id:
            dataframe_cache = self._registry.get("dataframe_runtime_cache")
            clear = getattr(dataframe_cache, "clear", None)
            if callable(clear):
                clear()
                dataframe_cleared = True

        return {
            "navigation": navigation_invalidated,
            "dataframe": dataframe_cleared,
        }

    def record_route_data(self, **payload: Any):
        """Record one lightweight route-data loading diagnostic entry."""
        diagnostics = self._registry.ensure(
            "workbench_route_data_diagnostics",
            WorkbenchRouteDataDiagnostics,
            expected_type=WorkbenchRouteDataDiagnostics,
            scope="session",
        )
        return diagnostics.record(**payload)

    def health_snapshot(self) -> dict[str, Any]:
        """Return lightweight diagnostics without exposing runtime objects."""
        lifecycle = self._registry.get("workbench_route_lifecycle")
        startup = self._registry.get("startup_diagnostics")
        return {
            "status": "ready",
            "route_lifecycle_ready": isinstance(lifecycle, WorkbenchRouteLifecycle),
            "startup_diagnostics_ready": isinstance(startup, StartupDiagnostics),
            "active_route": getattr(lifecycle, "active_route", ""),
        }
