"""Project-scoped runtime facade for interpretation presentation caches.

The facade keeps heavy DataFrame samples and Plotly figures out of Streamlit
session state and prevents UI code from constructing cache infrastructure.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable

import pandas as pd

from core.cache_metrics import CacheMetricsRegistry
from core.dataframe_runtime_cache import DEFAULT_DATAFRAME_CACHE_BYTES, DataframeRuntimeCache
from palettes.plot_cache import PlotBundle, PlotCache, PlotCacheStats


class InterpretationPresentationApplicationService:
    """Own project-scoped caches used by the interpretation presentation UI."""

    def __init__(
        self,
        *,
        root: Path | str,
        project_id: str,
        metrics_registry: CacheMetricsRegistry | None = None,
        dataframe_max_samples: int = 8,
        dataframe_max_bytes: int = DEFAULT_DATAFRAME_CACHE_BYTES,
        plot_max_entries: int = 4,
    ) -> None:
        clean_project_id = str(project_id).strip()
        if not clean_project_id:
            raise ValueError("project_id must not be empty")
        self._root = Path(root).resolve()
        self._project_id = clean_project_id
        self._metrics_registry = metrics_registry
        self._dataframe_max_samples = int(dataframe_max_samples)
        self._dataframe_max_bytes = int(dataframe_max_bytes)
        self._plot_max_entries = int(plot_max_entries)
        self._dataframe_cache: DataframeRuntimeCache | None = None
        self._plot_cache: PlotCache | None = None

    def _ensure_dataframe_cache(self) -> DataframeRuntimeCache:
        if self._dataframe_cache is None:
            metrics = None
            if self._metrics_registry is not None:
                metrics = self._metrics_registry.counter(
                    "dataframe_runtime", max_entries=self._dataframe_max_samples
                )
            self._dataframe_cache = DataframeRuntimeCache(
                max_samples=self._dataframe_max_samples,
                max_bytes=self._dataframe_max_bytes,
                metrics=metrics,
            )
        return self._dataframe_cache

    def _ensure_plot_cache(self) -> PlotCache:
        if self._plot_cache is None:
            self._plot_cache = PlotCache(max_entries=self._plot_max_entries)
        return self._plot_cache

    def dataframe_signature(
        self,
        frame: pd.DataFrame,
        *,
        revision: int,
        builder: Callable[[pd.DataFrame], str],
    ) -> str:
        return self._ensure_dataframe_cache().signature(
            frame, revision=revision, builder=builder
        )

    def screen_sample(
        self,
        frame: pd.DataFrame,
        *,
        source_signature: str,
        depth_range: tuple[float, float],
        max_rows: int,
        sampler: Callable[..., pd.DataFrame],
    ) -> pd.DataFrame:
        return self._ensure_dataframe_cache().screen_sample(
            frame,
            source_signature=source_signature,
            depth_range=depth_range,
            max_rows=max_rows,
            sampler=sampler,
        )

    def dataframe_stats(self):
        return self._ensure_dataframe_cache().stats()

    def get_plot_bundle(self, key: Hashable) -> PlotBundle | None:
        return self._ensure_plot_cache().get(key)

    def put_plot_bundle(
        self,
        key: Hashable,
        figures: Iterable[Any],
        *,
        tablet_figure: Any | None = None,
    ) -> PlotBundle:
        return self._ensure_plot_cache().put(
            key, figures, tablet_figure=tablet_figure
        )

    def plot_stats(self) -> PlotCacheStats:
        return self._ensure_plot_cache().stats()

    def clear_plots(self) -> None:
        if self._plot_cache is not None:
            self._plot_cache.clear()

    def clear(self) -> None:
        if self._dataframe_cache is not None:
            self._dataframe_cache.clear()
        self.clear_plots()

    def health_snapshot(self) -> dict[str, object]:
        return {
            "project_id": self._project_id,
            "root": str(self._root),
            "dataframe_cache_initialized": self._dataframe_cache is not None,
            "plot_cache_initialized": self._plot_cache is not None,
            "dataframe": (
                self._dataframe_cache.stats().to_dict()
                if self._dataframe_cache is not None
                else None
            ),
            "plot": (
                asdict(self._plot_cache.stats())
                if self._plot_cache is not None
                else None
            ),
        }
