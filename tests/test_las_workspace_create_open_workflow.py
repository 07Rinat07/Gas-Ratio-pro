from __future__ import annotations

from pathlib import Path

from projects.repository import create_project
from las_editor.las_creation_wizard import build_las_creation_wizard_draft
from las_editor.las_workspace_controller import LAS_WORKSPACE_DEFAULT_ID, LasWorkspaceController


def test_las_workspace_boundary_previews_create_las_without_ui_state_access(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Workflow", project_id="las-workflow")
    controller = LasWorkspaceController({}, tmp_path)
    draft = build_las_creation_wizard_draft(
        mode="template",
        well_name="WELL_A",
        start_depth=1000,
        stop_depth=1001,
        step=0.5,
        template_name="mud_gas",
    )

    result = controller.preview_create_las_workflow(project.id, draft, activate=False)

    assert result.workspace_state.workspace.id == LAS_WORKSPACE_DEFAULT_ID
    assert result.workspace_state.is_active is False
    assert result.preview.can_finalize is True
    assert "C1" in result.preview.data.columns
    assert "~ASCII" in result.preview.las_text


def test_las_workspace_boundary_creates_project_scoped_working_copy(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Save", project_id="las-save")
    state: dict[str, object] = {}
    controller = LasWorkspaceController(state, tmp_path)
    draft = build_las_creation_wizard_draft(
        mode="manual",
        well_name="SAVE_WELL",
        start_depth=10,
        stop_depth=11,
        step=0.5,
        curves=["GR"],
    )

    result = controller.create_las_working_copy(project.id, draft, filename="created_from_workspace")
    target = Path(result.manifest.target_path)

    assert result.manifest.is_ready is True
    assert target.exists()
    assert target.name == "created_from_workspace.las"
    assert f"workspaces/{LAS_WORKSPACE_DEFAULT_ID}/las/working_copies" in target.as_posix()
    assert state["active_workspace_id"] == LAS_WORKSPACE_DEFAULT_ID
    assert result.workspace.settings["last_created_las"] == str(target)
    assert result.workspace.settings["last_created_las_rows"] == 3
    assert result.workspace.settings["last_created_las_curves"] == 1


def test_las_workspace_boundary_blocks_unapproved_overwrite(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Overwrite", project_id="las-overwrite")
    controller = LasWorkspaceController({}, tmp_path)
    draft = build_las_creation_wizard_draft(
        well_name="OVERWRITE_WELL",
        start_depth=1,
        stop_depth=1,
        step=1,
    )

    first = controller.create_las_working_copy(project.id, draft, filename="same.las")
    second = controller.create_las_working_copy(project.id, draft, filename="same.las")

    assert first.manifest.is_ready is True
    assert second.manifest.is_ready is False
    assert second.manifest.status == "blocked"
    assert any(issue.code == "TARGET_ALREADY_EXISTS" for issue in second.manifest.issues)
