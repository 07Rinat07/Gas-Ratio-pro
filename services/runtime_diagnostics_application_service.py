"""Workspace-scoped application boundary for runtime diagnostics infrastructure.

UI code uses this service instead of constructing repository diagnostics,
health schedulers, and navigation caches directly. Heavy live objects remain in
``RuntimeServiceRegistry`` and never enter serializable session state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.cache_metrics import CacheMetricsRegistry
from core.project_navigation_runtime_cache import ProjectNavigationRuntimeCache
from core.repository_health import RepositoryHealthService
from core.repository_health_scheduler import RepositoryHealthScheduler
from core.repository_io import RepositoryIOMetrics
from core.runtime_diagnostics import RuntimeDiagnostics
from core.runtime_service_registry import RuntimeServiceRegistry


class RuntimeDiagnosticsApplicationService:
    """Coordinate workspace diagnostics and project-scoped health services."""

    def __init__(self, *, root: Path | str, registry: RuntimeServiceRegistry) -> None:
        self.root = Path(root).resolve()
        self._registry = registry
        self._active_project_id = ""

    def cache_metrics(self) -> CacheMetricsRegistry:
        """Return the single session-scoped cache telemetry registry."""
        return self._registry.ensure(
            "cache_metrics_registry",
            CacheMetricsRegistry,
            expected_type=CacheMetricsRegistry,
            scope="session",
        )


    def runtime_events(
        self,
        channel: str,
        *,
        max_events: int = 64,
    ) -> RuntimeDiagnostics:
        """Return a bounded session-scoped event collector for one UI channel.

        Channel names isolate interpretation, correlation, export, and other
        diagnostic streams while keeping their live ring buffers out of
        serializable session state.
        """
        clean_channel = str(channel or "").strip()
        if not clean_channel:
            raise ValueError("Diagnostics channel must not be empty.")
        clean_limit = int(max_events)
        if clean_limit < 1:
            raise ValueError("max_events must be positive.")
        key = f"runtime_diagnostics::{clean_channel}"
        collector = self._registry.get(key)
        if collector is not None:
            if not isinstance(collector, RuntimeDiagnostics):
                raise TypeError(f"Runtime service {key!r} has unexpected type {type(collector).__name__}.")
            return collector
        return self._registry.ensure(
            key,
            lambda: RuntimeDiagnostics(max_events=clean_limit),
            expected_type=RuntimeDiagnostics,
            scope="session",
        )

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
            "cache_metrics_ready": self._registry.get("cache_metrics_registry") is not None,
            "repository_metrics_ready": self._registry.get("repository_io_metrics") is not None,
            "runtime_event_channels": sum(
                1 for item in self._registry.descriptors()
                if item.key.startswith("runtime_diagnostics::")
            ),
            "navigation_cache_ready": self._registry.get("project_navigation_runtime_cache") is not None,
            "project_health_ready": self._registry.get("repository_health_service") is not None,
        }
