"""Project-scoped facade for expensive LAS-correlation render artifacts.

The service owns the bounded runtime cache so Plotly figures and correlation
panel objects never become Streamlit session-state values and UI code does not
construct cache infrastructure directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Hashable

from core.cache_metrics import CacheMetricsRegistry
from core.correlation_runtime_cache import CorrelationRenderArtifacts, CorrelationRuntimeCache


class CorrelationPresentationApplicationService:
    """Own the project-scoped cache used by LAS correlation presentation."""

    def __init__(
        self,
        *,
        root: Path | str,
        project_id: str,
        metrics_registry: CacheMetricsRegistry | None = None,
        max_entries: int = 3,
    ) -> None:
        clean_project_id = str(project_id).strip()
        if not clean_project_id:
            raise ValueError("project_id must not be empty")
        if int(max_entries) < 1:
            raise ValueError("max_entries must be positive")
        self._root = Path(root).resolve()
        self._project_id = clean_project_id
        self._metrics_registry = metrics_registry
        self._max_entries = int(max_entries)
        self._cache: CorrelationRuntimeCache | None = None

    def _ensure_cache(self) -> CorrelationRuntimeCache:
        if self._cache is None:
            metrics = None
            if self._metrics_registry is not None:
                metrics = self._metrics_registry.counter(
                    f"correlation_render::{self._project_id}",
                    max_entries=self._max_entries,
                )
            self._cache = CorrelationRuntimeCache(
                max_entries=self._max_entries,
                metrics=metrics,
            )
        return self._cache

    def get(self, key: Hashable) -> CorrelationRenderArtifacts | None:
        return self._ensure_cache().get(key)

    def put(self, key: Hashable, artifacts: CorrelationRenderArtifacts) -> None:
        if not isinstance(artifacts, CorrelationRenderArtifacts):
            raise TypeError("artifacts must be CorrelationRenderArtifacts")
        self._ensure_cache().put(key, artifacts)

    def put_artifacts(
        self,
        key: Hashable,
        *,
        studio_panel=None,
        studio_figure=None,
        figure=None,
        figure_title: str = "",
        figure_file_name: str = "",
    ) -> CorrelationRenderArtifacts:
        """Construct and cache correlation artifacts behind the application boundary."""
        artifacts = CorrelationRenderArtifacts(
            studio_panel=studio_panel,
            studio_figure=studio_figure,
            figure=figure,
            figure_title=str(figure_title),
            figure_file_name=str(figure_file_name),
        )
        self._ensure_cache().put(key, artifacts)
        return artifacts

    def invalidate(self, key: Hashable | None = None) -> int:
        if self._cache is None:
            return 0
        return self._cache.invalidate(key)

    def clear(self) -> int:
        return self.invalidate()

    def health_snapshot(self) -> dict[str, object]:
        return {
            "service": type(self).__name__,
            "project_id": self._project_id,
            "root": str(self._root),
            "cache_initialized": self._cache is not None,
            "entries": len(self._cache) if self._cache is not None else 0,
            "max_entries": self._max_entries,
        }
