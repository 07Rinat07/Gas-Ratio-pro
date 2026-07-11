from __future__ import annotations

from core.workbench_controller import build_workbench_controller
from core.workbench_las_primary_module import LAS_PRIMARY_STATE_KEY, LAS_PRIMARY_LAST_EXPORT_KEY
from services.las_manager_service import LasManagerService
from tests.test_las_manager_service import SIMPLE_LAS


def _state(tmp_path):
    record = LasManagerService(tmp_path).save_file(
        project_id="demo",
        data=SIMPLE_LAS,
        file_name="demo.las",
        well_name="Demo Well",
        version_label="raw",
    ).record
    return {
        "projects_root": str(tmp_path),
        "active_project_id": "demo",
        "active_las_id": record.id,
    }, record.id


def _las_view(controller):
    return next(item for item in controller.view_model()["tool_views"]["items"] if item["id"] == "tool.las_viewer")


def test_primary_las_module_activation_synchronizes_context_tool_navigation_and_dock(tmp_path):
    state, las_id = _state(tmp_path)
    controller = build_workbench_controller(state)

    result = controller.dispatch_renderer_action("action.las_primary_activate", {"project_id": "demo", "las_id": las_id})
    payload = result.view_model()

    assert result.command_result.executed is True
    assert state[LAS_PRIMARY_STATE_KEY]["status"] == "ready"
    assert payload["interaction"]["active_navigation_id"] == "nav.las_workspace"
    assert payload["active_tool_id"] == "tool.las_viewer"
    assert payload["interaction"]["active_dock_pane_id"] == "dock.tool.las_viewer"
    assert state[LAS_PRIMARY_STATE_KEY]["raw_dataframe_included"] is False


def test_primary_las_module_exposes_renderer_neutral_lifecycle_and_actions(tmp_path):
    state, las_id = _state(tmp_path)
    controller = build_workbench_controller(state)
    controller.dispatch_renderer_action("action.las_primary_activate", {"project_id": "demo", "las_id": las_id})

    view = _las_view(controller)
    primary = view["content"]["primary_module"]
    action_ids = {item["id"] for item in view["actions"]}

    assert primary["primary_module"] is True
    assert primary["renderer_neutral"] is True
    assert primary["raw_dataframe_included"] is False
    assert {"action.las_primary_zoom", "action.las_primary_pan", "action.las_primary_fit", "action.las_primary_reset", "action.las_primary_export"} <= action_ids


def test_primary_las_navigation_persists_compact_viewer_state(tmp_path):
    state, las_id = _state(tmp_path)
    controller = build_workbench_controller(state)
    controller.dispatch_renderer_action("action.las_primary_activate", {"project_id": "demo", "las_id": las_id})

    zoom = controller.dispatch_renderer_action("action.las_primary_zoom", {"factor": 2.0})
    reset = controller.dispatch_renderer_action("action.las_primary_reset", {})

    assert zoom.command_result.result["last_operation"] == "zoom"
    assert reset.command_result.result["last_operation"] == "reset"
    assert state[LAS_PRIMARY_STATE_KEY]["viewer_state"]["las_id"] == las_id
    assert state[LAS_PRIMARY_STATE_KEY]["raw_dataframe_included"] is False
    assert all(type(value).__module__.split(".")[0] != "pandas" for value in state[LAS_PRIMARY_STATE_KEY].values())


def test_primary_las_export_uses_current_view_and_stores_only_export_metadata(tmp_path):
    state, las_id = _state(tmp_path)
    controller = build_workbench_controller(state)
    controller.dispatch_renderer_action("action.las_primary_activate", {"project_id": "demo", "las_id": las_id})

    result = controller.dispatch_renderer_action("action.las_primary_export", {})

    assert result.command_result.result["export"]["geometry_signature_match"] is True
    assert result.command_result.result["export"]["ok"] is True
    assert state[LAS_PRIMARY_LAST_EXPORT_KEY]["svg"]["byte_size"] > 0
    assert state[LAS_PRIMARY_LAST_EXPORT_KEY]["pdf"]["byte_size"] > 0
    assert "content" not in state[LAS_PRIMARY_LAST_EXPORT_KEY]["svg"]
