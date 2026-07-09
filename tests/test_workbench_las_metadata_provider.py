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
