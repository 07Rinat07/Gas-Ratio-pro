from pathlib import Path

from core.runtime_service_registry import RuntimeServiceRegistry
from services.runtime_diagnostics_application_service import RuntimeDiagnosticsApplicationService


def test_route_lifecycle_and_startup_diagnostics_are_owned_by_application_service(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    service = RuntimeDiagnosticsApplicationService(root=tmp_path, registry=registry)

    first = service.activate_workbench_route("nav.dashboard")
    second = service.activate_workbench_route("nav.data")
    startup = service.record_startup_cycle(
        {"page_config": 1.0, "total": 2.0},
        route_id="nav.data",
        project_id="project-a",
    )

    assert first.active_route == "nav.dashboard"
    assert second.changed is True
    assert second.previous_route == "nav.dashboard"
    assert startup["route_id"] == "nav.data"
    snapshot = service.health_snapshot()
    assert snapshot["route_lifecycle_ready"] is True
    assert snapshot["startup_diagnostics_ready"] is True


def test_project_cache_coherence_is_hidden_behind_application_service(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    service = RuntimeDiagnosticsApplicationService(root=tmp_path, registry=registry)

    class NavigationCache:
        def __init__(self) -> None:
            self.invalidations = []

        def invalidate(self, project_id: str, *, reason: str) -> None:
            self.invalidations.append((project_id, reason))

    class DataframeCache:
        def __init__(self) -> None:
            self.clear_count = 0

        def clear(self) -> None:
            self.clear_count += 1

    navigation = registry.set("project_navigation_runtime_cache", NavigationCache())
    dataframe = registry.set("dataframe_runtime_cache", DataframeCache())
    metrics = service.subscribe_project_cache_coherence(
        "test-cache-coherence", active_project_id=lambda: "project-a"
    )

    metrics._publish_mutation({"project_id": "project-a", "operation": "save"})

    assert navigation.invalidations == [("project-a", "repository-save")]
    assert dataframe.clear_count == 1


def test_streamlit_ui_does_not_import_runtime_registry() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "from core.runtime_service_registry import runtime_service_registry" not in source
    assert "runtime_service_registry(" not in source
