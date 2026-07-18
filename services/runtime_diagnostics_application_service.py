"""Workspace-scoped application boundary for runtime diagnostics infrastructure.

UI code uses this service instead of constructing repository diagnostics,
health schedulers, and navigation caches directly. Heavy live objects remain in
``RuntimeServiceRegistry`` and never enter serializable session state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from core.project_navigation_runtime_cache import ProjectNavigationRuntimeCache
from core.repository_health import RepositoryHealthService
from core.repository_health_scheduler import RepositoryHealthScheduler
from core.repository_io import RepositoryIOMetrics
from core.runtime_service_registry import RuntimeServiceRegistry
from services.workbench_runtime_application_service import WorkbenchRuntimeApplicationService


class RuntimeDiagnosticsApplicationService:
    """Coordinate workspace diagnostics and project-scoped health services."""

    def __init__(self, *, root: Path | str, registry: RuntimeServiceRegistry) -> None:
        self.root = Path(root).resolve()
        self._registry = registry
        self._active_project_id = ""

    def _workbench_runtime(self) -> WorkbenchRuntimeApplicationService:
        return self._registry.ensure(
            "workbench_runtime_application_service",
            lambda: WorkbenchRuntimeApplicationService(registry=self._registry),
            expected_type=WorkbenchRuntimeApplicationService,
            scope="session",
        )

    def activate_workbench_route(self, route_id: str):
        """Activate one Workbench route through the application boundary."""
        return self._workbench_runtime().activate_route(route_id)

    def record_startup_cycle(
        self,
        stages_ms: Mapping[str, float],
        *,
        route_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        """Record one startup/rerun cycle without exposing diagnostics objects."""
        return self._workbench_runtime().record_startup_cycle(
            stages_ms, route_id=route_id, project_id=project_id
        )

    def subscribe_project_cache_coherence(
        self,
        subscriber_id: str,
        *,
        active_project_id: Callable[[], str],
    ) -> RepositoryIOMetrics:
        """Keep project navigation and DataFrame caches coherent after mutations."""
        runtime = self._workbench_runtime()

        def _invalidate(event: dict[str, Any]) -> None:
            project_id = str(event.get("project_id") or "").strip()
            operation = str(event.get("operation") or "mutation").strip()
            runtime.invalidate_project_runtime_caches(
                project_id,
                active_project_id=str(active_project_id() or ""),
                reason=f"repository-{operation}",
            )

        return self.subscribe_repository_mutations(subscriber_id, _invalidate)

    def repository_metrics(self) -> RepositoryIOMetrics:
        """Return the single session-scoped repository telemetry collector."""
        return self._registry.ensure(
            "repository_io_metrics",
            RepositoryIOMetrics,
            expected_type=RepositoryIOMetrics,
            scope="session",
        )

    def subscribe_repository_mutations(
        self,
        subscriber_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> RepositoryIOMetrics:
        """Register an idempotent mutation subscriber and return the collector."""
        metrics = self.repository_metrics()
        metrics.subscribe_mutations(str(subscriber_id), callback)
        return metrics

    def navigation_cache(self) -> ProjectNavigationRuntimeCache:
        """Return the session-scoped project navigation runtime cache."""
        return self._registry.ensure(
            "project_navigation_runtime_cache",
            ProjectNavigationRuntimeCache,
            expected_type=ProjectNavigationRuntimeCache,
            scope="session",
        )

    def prepare_project_health(
        self,
        project_id: str,
        *,
        interval_seconds: float = 300.0,
        scan_ttl_seconds: float = 0.0,
    ) -> RepositoryHealthScheduler:
        """Create or reuse the health scheduler for the selected project."""
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            raise ValueError("Project id must not be empty.")

        project_root = (self.root / clean_project_id).resolve()
        key = f"repository_health_service::{clean_project_id}::{project_root}"
        scheduler = self._registry.ensure(
            key,
            lambda: RepositoryHealthScheduler(
                RepositoryHealthService(project_root, scan_ttl_seconds=scan_ttl_seconds),
                interval_seconds=interval_seconds,
            ),
            expected_type=RepositoryHealthScheduler,
            scope="project",
        )
        # Compatibility alias consumed by the existing Diagnostics Center.
        self._registry.set("repository_health_service", scheduler, scope="project")
        self._active_project_id = clean_project_id
        return scheduler

    def health_snapshot(self) -> dict[str, Any]:
        """Return lightweight service diagnostics without exposing live objects."""
        return {
            "status": "ready",
            "root": str(self.root),
            "active_project_id": self._active_project_id,
            "repository_metrics_ready": self._registry.get("repository_io_metrics") is not None,
            "navigation_cache_ready": self._registry.get("project_navigation_runtime_cache") is not None,
            "project_health_ready": self._registry.get("repository_health_service") is not None,
            "route_lifecycle_ready": self._workbench_runtime().health_snapshot()["route_lifecycle_ready"],
            "startup_diagnostics_ready": self._workbench_runtime().health_snapshot()["startup_diagnostics_ready"],
        }
