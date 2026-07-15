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


def test_runtime_event_collectors_are_lazy_reused_and_channel_isolated(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    service = RuntimeDiagnosticsApplicationService(root=tmp_path, registry=registry)

    interpretation = service.runtime_events("interpretation.presentation", max_events=8)
    interpretation_again = service.runtime_events("interpretation.presentation", max_events=32)
    correlation = service.runtime_events("correlation.presentation", max_events=16)

    assert interpretation is interpretation_again
    assert interpretation.max_events == 8
    assert correlation is not interpretation
    assert correlation.max_events == 16
    assert service.health_snapshot()["runtime_event_channels"] == 2
    assert all(
        item.scope == "session"
        for item in registry.descriptors()
        if item.key.startswith("runtime_diagnostics::")
    )


def test_runtime_event_collector_rejects_invalid_arguments(tmp_path: Path) -> None:
    service = RuntimeDiagnosticsApplicationService(root=tmp_path, registry=RuntimeServiceRegistry())

    with pytest.raises(ValueError):
        service.runtime_events("  ")
    with pytest.raises(ValueError):
        service.runtime_events("interpretation", max_events=0)


def test_streamlit_ui_resolves_runtime_diagnostics_through_application_service() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "from core.runtime_diagnostics import RuntimeDiagnostics" not in source
    assert "lambda: RuntimeDiagnostics(" not in source
    assert '.runtime_events("interpretation.presentation"' not in source  # multiline API remains explicit below
    assert '"interpretation.presentation", max_events=64' in source
    assert '"correlation.presentation", max_events=128' in source
