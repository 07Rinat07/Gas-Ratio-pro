from pathlib import Path

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from services.interpretation_correlation_application_service import (
    InterpretationCorrelationApplicationService,
)


def test_correlation_service_resolves_repository_metrics_through_diagnostics(tmp_path: Path) -> None:
    state: dict[str, object] = {}
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry, state)

    service = container.correlation(project_id="demo", root=tmp_path)
    diagnostics = container.runtime_diagnostics(root=tmp_path)

    assert isinstance(service, InterpretationCorrelationApplicationService)
    assert diagnostics.repository_metrics() is registry.get("repository_io_metrics")
    assert diagnostics.health_snapshot()["repository_metrics_ready"] is True


def test_correlation_service_does_not_create_duplicate_metrics_collectors(tmp_path: Path) -> None:
    state: dict[str, object] = {}
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry, state)

    first = container.correlation(project_id="alpha", root=tmp_path)
    metrics = container.runtime_diagnostics(root=tmp_path).repository_metrics()
    second = container.correlation(project_id="beta", root=tmp_path)

    assert first is not second
    assert container.runtime_diagnostics(root=tmp_path).repository_metrics() is metrics


def test_correlation_ui_does_not_construct_repository_metrics_directly() -> None:
    source = Path("ui/interpretation_correlation_panel.py").read_text(encoding="utf-8")

    assert "RepositoryIOMetrics" not in source
    assert "runtime_service_registry" not in source
    assert 'registry.ensure("repository_io_metrics"' not in source
    assert "application_service_container(state).correlation" in source
