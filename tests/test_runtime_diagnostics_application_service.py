from pathlib import Path

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from services.runtime_diagnostics_application_service import RuntimeDiagnosticsApplicationService


def test_container_reuses_workspace_scoped_runtime_diagnostics_service(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry)

    first = container.runtime_diagnostics(root=tmp_path)
    second = container.runtime_diagnostics(root=tmp_path)

    assert isinstance(first, RuntimeDiagnosticsApplicationService)
    assert first is second
    assert container.snapshot()["active"] == 1


def test_runtime_diagnostics_creates_shared_metrics_and_navigation_cache(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    service = RuntimeDiagnosticsApplicationService(root=tmp_path, registry=registry)

    assert service.cache_metrics() is service.cache_metrics()
    assert service.repository_metrics() is service.repository_metrics()
    assert service.navigation_cache() is service.navigation_cache()
    snapshot = service.health_snapshot()
    assert snapshot["cache_metrics_ready"] is True
    assert snapshot["repository_metrics_ready"] is True
    assert snapshot["navigation_cache_ready"] is True


def test_project_health_is_isolated_by_project_and_publishes_compatibility_alias(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    service = RuntimeDiagnosticsApplicationService(root=tmp_path, registry=registry)

    alpha = service.prepare_project_health("alpha")
    alpha_again = service.prepare_project_health("alpha")
    beta = service.prepare_project_health("beta")

    assert alpha is alpha_again
    assert beta is not alpha
    assert registry.get("repository_health_service") is beta
    assert service.health_snapshot()["active_project_id"] == "beta"


def test_project_health_rejects_empty_project_id(tmp_path: Path) -> None:
    service = RuntimeDiagnosticsApplicationService(
        root=tmp_path, registry=RuntimeServiceRegistry()
    )
    with pytest.raises(ValueError):
        service.prepare_project_health("  ")
