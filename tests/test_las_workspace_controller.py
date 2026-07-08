from __future__ import annotations

from projects.repository import create_project

from las_editor.las_workspace_controller import (
    LAS_WORKSPACE_DEFAULT_ID,
    LAS_WORKSPACE_DEFAULT_NAME,
    LAS_WORKSPACE_KIND,
    LAS_WORKSPACE_SCHEMA,
    LasWorkspaceController,
    default_las_workspace_settings,
)


def test_las_workspace_controller_creates_and_activates_project_workspace(tmp_path):
    state: dict[str, str] = {}
    controller = LasWorkspaceController(state, tmp_path)
    create_project(tmp_path, name="Project A", project_id="project-a")

    result = controller.ensure_project_las_workspace("project-a", recent_files=("well_a.las",))

    assert result.schema == LAS_WORKSPACE_SCHEMA
    assert result.project_id == "project-a"
    assert result.workspace.id == LAS_WORKSPACE_DEFAULT_ID
    assert result.workspace.name == LAS_WORKSPACE_DEFAULT_NAME
    assert result.workspace.kind == LAS_WORKSPACE_KIND
    assert result.workspace.settings["workspace_version"] == "3.0"
    assert result.workspace.settings["schema"] == LAS_WORKSPACE_SCHEMA
    assert result.is_active is True
    assert state["active_workspace_id"] == LAS_WORKSPACE_DEFAULT_ID
    assert result.home.title == "LAS Workspace 2.0"
    assert result.home.recent_files == ("well_a.las",)


def test_las_workspace_controller_reopens_existing_workspace_without_duplicate(tmp_path):
    state: dict[str, str] = {}
    controller = LasWorkspaceController(state, tmp_path)
    create_project(tmp_path, name="Project A", project_id="project-a")

    first = controller.ensure_project_las_workspace("project-a")
    second = controller.open_project_las_workspace("project-a")

    assert first.workspace.id == second.workspace.id
    assert second.created is False
    assert second.is_active is True

    workspaces = controller.workspace_controller.list_project_workspaces("project-a")
    assert len(workspaces) == 1
    assert workspaces[0].is_active is True


def test_default_las_workspace_settings_describe_required_tools():
    settings = default_las_workspace_settings()

    assert settings["schema"] == LAS_WORKSPACE_SCHEMA
    assert settings["workspace_version"] == "3.0"
    for tool in ("create_las", "open_las", "import_csv", "import_excel", "templates", "validator"):
        assert tool in settings["enabled_tools"]
