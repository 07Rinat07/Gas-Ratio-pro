from pathlib import Path

from core.application_service_container import application_service_container
from core.runtime_service_registry import runtime_service_registry
from services.workbench_runtime_application_service import WorkbenchRuntimeApplicationService


class _NavigationCache:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def invalidate(self, project_id: str, *, reason: str) -> None:
        self.calls.append((project_id, reason))


class _DataframeCache:
    def __init__(self) -> None:
        self.clear_count = 0

    def clear(self) -> None:
        self.clear_count += 1


def test_workbench_runtime_service_is_session_scoped_and_reused() -> None:
    state = {}
    container = application_service_container(state)

    first = container.workbench_runtime()
    second = container.workbench_runtime()

    assert first is second
    assert isinstance(first, WorkbenchRuntimeApplicationService)
    descriptor = next(
        item for item in container.descriptors()
        if item.service_name == "workbench_runtime"
    )
    assert descriptor.project_id == "__session__"


def test_route_lifecycle_and_startup_diagnostics_are_lazy() -> None:
    state = {}
    service = application_service_container(state).workbench_runtime()

    assert service.health_snapshot()["route_lifecycle_ready"] is False
    first = service.activate_route("nav.dashboard")
    second = service.activate_route("nav.data")
    record = service.record_startup_cycle(
        {"page_config": 1.0, "total": 2.0},
        route_id="nav.data",
        project_id="demo",
    )

    assert first.changed is False
    assert second.changed is True
    assert record["route_id"] == "nav.data"
    snapshot = service.health_snapshot()
    assert snapshot["route_lifecycle_ready"] is True
    assert snapshot["startup_diagnostics_ready"] is True
    assert snapshot["active_route"] == "nav.data"


def test_project_cache_invalidation_is_explicit_and_project_aware() -> None:
    state = {}
    registry = runtime_service_registry(state)
    navigation = registry.set("project_navigation_runtime_cache", _NavigationCache())
    dataframe = registry.set("dataframe_runtime_cache", _DataframeCache())
    service = application_service_container(state).workbench_runtime()

    unrelated = service.invalidate_project_runtime_caches(
        "project-b", active_project_id="project-a", reason="repository-save"
    )
    active = service.invalidate_project_runtime_caches(
        "project-a", active_project_id="project-a", reason="repository-delete"
    )

    assert unrelated == {"navigation": True, "dataframe": False}
    assert active == {"navigation": True, "dataframe": True}
    assert navigation.calls == [
        ("project-b", "repository-save"),
        ("project-a", "repository-delete"),
    ]
    assert dataframe.clear_count == 1


def test_streamlit_ui_does_not_access_runtime_registry_directly() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "runtime_service_registry" not in source
    assert "RuntimeServiceRegistry" not in source
    assert ".ensure(\"workbench_route_lifecycle\"" not in source
    assert ".ensure(\"startup_diagnostics\"" not in source
