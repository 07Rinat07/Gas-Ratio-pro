from __future__ import annotations

from pathlib import Path

import pytest

from core.application_service_container import application_service_container
from core.cache_metrics import CacheMetricsRegistry
from core.correlation_runtime_cache import CorrelationRenderArtifacts
from services.correlation_presentation_application_service import (
    CorrelationPresentationApplicationService,
)


def _artifacts(label: str) -> CorrelationRenderArtifacts:
    return CorrelationRenderArtifacts(
        studio_panel={"label": label},
        studio_figure={"studio": label},
        figure={"main": label},
        figure_title=f"title-{label}",
        figure_file_name=f"file-{label}",
    )


def test_service_is_lazy_and_health_is_lightweight(tmp_path: Path) -> None:
    service = CorrelationPresentationApplicationService(
        root=tmp_path,
        project_id="project-a",
        metrics_registry=CacheMetricsRegistry(),
    )

    health = service.health_snapshot()

    assert health["project_id"] == "project-a"
    assert health["cache_initialized"] is False
    assert health["entries"] == 0


def test_service_stores_reuses_and_clears_artifacts(tmp_path: Path) -> None:
    service = CorrelationPresentationApplicationService(
        root=tmp_path, project_id="project-a", max_entries=2
    )
    value = _artifacts("a")

    assert service.get(("missing",)) is None
    service.put(("a",), value)
    assert service.get(("a",)) is value
    assert service.health_snapshot()["entries"] == 1
    assert service.clear() == 1
    assert service.health_snapshot()["entries"] == 0


def test_service_enforces_bounded_cache_and_artifact_contract(tmp_path: Path) -> None:
    service = CorrelationPresentationApplicationService(
        root=tmp_path, project_id="project-a", max_entries=2
    )
    service.put(("a",), _artifacts("a"))
    service.put(("b",), _artifacts("b"))
    service.put(("c",), _artifacts("c"))

    assert service.get(("a",)) is None
    assert service.get(("b",)) is not None
    assert service.get(("c",)) is not None
    with pytest.raises(TypeError):
        service.put(("invalid",), object())  # type: ignore[arg-type]


def test_container_reuses_per_project_and_isolates_projects(tmp_path: Path) -> None:
    state: dict[str, object] = {}
    container = application_service_container(state)

    first = container.correlation_presentation(project_id="project-a", root=tmp_path)
    same = container.correlation_presentation(project_id="project-a", root=tmp_path)
    other = container.correlation_presentation(project_id="project-b", root=tmp_path)

    assert first is same
    assert first is not other


def test_empty_project_id_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        CorrelationPresentationApplicationService(root=tmp_path, project_id=" ")
