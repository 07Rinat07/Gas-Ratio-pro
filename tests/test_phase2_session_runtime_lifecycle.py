from __future__ import annotations

from core.diagnostics_center import build_diagnostics_center_snapshot
from core.runtime_service_registry import RuntimeServiceRegistry, runtime_service_registry
from core.session_state_audit import audit_session_state
from core.session_state_manager import clear_on_workspace_change


class ClosableService:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_runtime_registry_shuts_down_only_requested_scope() -> None:
    registry = RuntimeServiceRegistry()
    session_service = registry.set("session", ClosableService(), scope="session")
    workspace_service = registry.set("workspace", ClosableService(), scope="workspace")

    results = registry.shutdown_scopes({"workspace"})

    assert [item.key for item in results] == ["workspace"]
    assert workspace_service.closed is True
    assert session_service.closed is False
    assert [item.key for item in registry.descriptors()] == ["session"]


def test_workspace_cleanup_disposes_workspace_runtime_services_only() -> None:
    state: dict[str, object] = {
        "active_project_id": "p",
        "active_well_id": "w",
        "active_las_id": "l",
        "active_workspace_id": "old",
        "workspace_local_table": [1],
    }
    registry = runtime_service_registry(state)
    workspace_service = registry.set("correlation_cache", ClosableService(), scope="workspace")
    session_service = registry.set("metrics", ClosableService(), scope="session")

    result = clear_on_workspace_change(state, "p", "w", "l", "new")

    assert workspace_service.closed is True
    assert session_service.closed is False
    assert [item.key for item in result.runtime_shutdown] == ["correlation_cache"]
    assert "workspace_local_table" not in state


def test_session_audit_reports_ownership_and_unregistered_keys() -> None:
    state = {
        "runtime::services": object(),
        "correlation_view": {},
        "theme": "dark",
        "legacy_custom_key": 1,
    }

    audit = audit_session_state(state).to_dict()

    assert audit["owner_counts"]["runtime"] == 1
    assert audit["lifecycle_counts"]["transient"] == 1
    assert "legacy_custom_key" in audit["unregistered_keys"]


def test_diagnostics_center_exposes_scopes_without_changing_service_contract() -> None:
    state: dict[str, object] = {}
    registry = runtime_service_registry(state)
    registry.set("cache", object(), scope="workspace")

    snapshot = build_diagnostics_center_snapshot(state)

    assert snapshot["runtime"]["services"] == [{"key": "cache", "type_name": "object"}]
    assert snapshot["runtime"]["service_scopes"] == {"cache": "workspace"}
