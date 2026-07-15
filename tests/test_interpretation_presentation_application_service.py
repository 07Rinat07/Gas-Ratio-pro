from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.application_service_container import application_service_container
from core.cache_metrics import CacheMetricsRegistry
from services.interpretation_presentation_application_service import (
    InterpretationPresentationApplicationService,
)


def test_service_is_lazy_and_reports_lightweight_health(tmp_path: Path) -> None:
    service = InterpretationPresentationApplicationService(
        root=tmp_path, project_id="project-a", metrics_registry=CacheMetricsRegistry()
    )

    health = service.health_snapshot()

    assert health["project_id"] == "project-a"
    assert health["dataframe_cache_initialized"] is False
    assert health["plot_cache_initialized"] is False
    assert health["dataframe"] is None
    assert health["plot"] is None


def test_dataframe_signature_and_samples_are_reused(tmp_path: Path) -> None:
    service = InterpretationPresentationApplicationService(
        root=tmp_path, project_id="project-a"
    )
    frame = pd.DataFrame({"DEPTH": [1000.0, 1001.0], "C1": [1.0, 2.0]})
    builder_calls = 0
    sampler_calls = 0

    def builder(value: pd.DataFrame) -> str:
        nonlocal builder_calls
        builder_calls += 1
        return f"rows:{len(value)}"

    def sampler(value: pd.DataFrame, *, max_rows: int) -> pd.DataFrame:
        nonlocal sampler_calls
        sampler_calls += 1
        return value.head(max_rows)

    first = service.dataframe_signature(frame, revision=1, builder=builder)
    second = service.dataframe_signature(frame, revision=1, builder=builder)
    sample_a = service.screen_sample(
        frame,
        source_signature=first,
        depth_range=(1000.0, 1001.0),
        max_rows=10,
        sampler=sampler,
    )
    sample_b = service.screen_sample(
        frame,
        source_signature=first,
        depth_range=(1000.0, 1001.0),
        max_rows=10,
        sampler=sampler,
    )

    assert first == second == "rows:2"
    assert builder_calls == 1
    assert sampler_calls == 1
    assert sample_a is sample_b
    assert service.dataframe_stats().sample_hits == 1


def test_plot_cache_is_owned_by_service(tmp_path: Path) -> None:
    service = InterpretationPresentationApplicationService(
        root=tmp_path, project_id="project-a"
    )
    figure = {"data": [], "layout": {"title": "test"}}

    assert service.get_plot_bundle(("key",)) is None
    stored = service.put_plot_bundle(("key",), [figure])
    cached = service.get_plot_bundle(("key",))

    assert cached is stored
    assert service.plot_stats().hits == 1
    service.clear_plots()
    assert service.get_plot_bundle(("key",)) is None


def test_container_reuses_service_per_project_and_isolates_projects(tmp_path: Path) -> None:
    state: dict[str, object] = {}
    container = application_service_container(state)

    first = container.interpretation_presentation(
        project_id="project-a", root=tmp_path
    )
    same = container.interpretation_presentation(
        project_id="project-a", root=tmp_path
    )
    other = container.interpretation_presentation(
        project_id="project-b", root=tmp_path
    )

    assert first is same
    assert first is not other
