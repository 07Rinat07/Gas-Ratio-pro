from __future__ import annotations

from core.workbench_controller import build_workbench_controller
from services.las_manager_service import LasManagerService
from tests.test_las_manager_service import SIMPLE_LAS


def _item(payload: dict, tool_id: str) -> dict:
    return next(item for item in payload["items"] if item["id"] == tool_id)


def test_las_viewer_provider_exposes_curve_metadata_from_project_storage(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(
        project_id="demo",
        data=SIMPLE_LAS,
        file_name="demo.las",
        well_name="Demo Well",
        version_label="raw",
    ).record
    state = {
        "projects_root": str(tmp_path),
        "active_project_id": "demo",
        "active_las_id": record.id,
    }
    controller = build_workbench_controller(state)

    las_view = _item(controller.view_model()["tool_views"], "tool.las_viewer")
    metadata = las_view["content"]["curve_metadata"]

    assert las_view["status"] == "ready"
    assert las_view["content"]["metadata_error"] == ""
    assert metadata["curve_count"] == 2
    assert metadata["row_count"] == 2
    assert metadata["depth_curve"] == "DEPT"
    assert metadata["quality_flags"] == []
    assert las_view["content"]["selected_las"]["well_name"] == "Demo Well"


def test_las_viewer_provider_exposes_visualization_payload_from_project_storage(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(
        project_id="demo",
        data=SIMPLE_LAS,
        file_name="demo.las",
        well_name="Demo Well",
        version_label="raw",
    ).record
    state = {
        "projects_root": str(tmp_path),
        "active_project_id": "demo",
        "active_las_id": record.id,
    }

    las_view = _item(build_workbench_controller(state).view_model()["tool_views"], "tool.las_viewer")
    visualization = las_view["content"]["visualization"]

    assert las_view["content"]["visualization_error"] == ""
    assert visualization["depth_curve"] == "DEPT"
    assert visualization["depth_range"] == {"start": 1000.0, "stop": 1000.5, "step": 0.5}
    assert visualization["tracks"][0]["id"] == "track.gamma"
    assert visualization["curves"][0]["mnemonic"] == "GR"
    assert "points" in visualization["curves"][0]
