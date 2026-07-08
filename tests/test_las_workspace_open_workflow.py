from __future__ import annotations

from pathlib import Path

import pytest

from projects.repository import create_project
from las_editor.las_creation_wizard import build_las_creation_wizard_draft
from las_editor.las_workspace_controller import LAS_WORKSPACE_DEFAULT_ID, LasWorkspaceController


def _draft():
    return build_las_creation_wizard_draft(
        mode="manual",
        well_name="OPEN_WELL",
        start_depth=100,
        stop_depth=101,
        step=0.5,
        curves=["GR", "C1"],
    )


def test_las_workspace_lists_saved_working_copies_without_activating_state(tmp_path: Path):
    project = create_project(tmp_path, name="LAS List", project_id="las-list")
    state: dict[str, object] = {}
    controller = LasWorkspaceController(state, tmp_path)

    controller.create_las_working_copy(project.id, _draft(), filename="second.las")
    controller.create_las_working_copy(project.id, _draft(), filename="first.las")
    controller.workspace_controller.close_workspace()

    items = controller.list_las_working_copies(project.id)

    assert [item.filename for item in items] == ["first.las", "second.las"]
    assert all(f"workspaces/{LAS_WORKSPACE_DEFAULT_ID}/las/working_copies" in item.path for item in items)
    assert state.get("active_workspace_id", "") == ""


def test_las_workspace_opens_saved_working_copy_through_controller(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Open", project_id="las-open")
    state: dict[str, object] = {}
    controller = LasWorkspaceController(state, tmp_path)
    workspace_state = controller.ensure_project_las_workspace(project.id, activate=False)
    copies_dir = controller._working_copies_dir(project.id, workspace_state.workspace.id)
    copies_dir.mkdir(parents=True, exist_ok=True)
    sample = Path("examples/sample_gas_data.las").read_text(encoding="utf-8")
    (copies_dir / "open_me.las").write_text(sample, encoding="utf-8")

    result = controller.open_las_working_copy(project.id, "open_me.las")

    assert result.item.filename == "open_me.las"
    assert list(result.data.columns) == ["DEPT", "C1", "C2", "C3", "IC4", "NC4", "IC5", "NC5"]
    assert len(result.data) == 3
    assert state["active_workspace_id"] == LAS_WORKSPACE_DEFAULT_ID
    assert result.workspace.settings["last_opened_las"] == result.item.path
    assert result.workspace.settings["last_opened_las_rows"] == 3
    assert result.workspace.settings["last_opened_las_curves"] == 8


def test_las_workspace_open_rejects_missing_working_copy(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Missing", project_id="las-missing")
    controller = LasWorkspaceController({}, tmp_path)

    with pytest.raises(FileNotFoundError):
        controller.open_las_working_copy(project.id, "missing.las")
