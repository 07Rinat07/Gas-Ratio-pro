from __future__ import annotations

import pytest

from projects.repository import create_project
from projects.workspace_manager import WorkspaceManager


def test_workspace_manager_creates_lists_and_marks_active_workspace(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    manager = WorkspaceManager(tmp_path)

    created = manager.create_project_workspace(
        project.id,
        "LAS Workspace",
        kind="las",
        settings={"depth_unit": "m", "track": "GR"},
        workspace_id="las-main",
    )
    items = manager.list_project_workspaces(project.id, active_workspace_id="las-main")

    assert created.workspace.id == "las-main"
    assert len(items) == 1
    assert items[0].name == "LAS Workspace"
    assert items[0].kind == "las"
    assert items[0].settings_count == 2
    assert items[0].is_active is True


def test_workspace_manager_updates_settings_through_service_boundary(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    manager = WorkspaceManager(tmp_path)
    manager.create_project_workspace(
        project.id,
        "Correlation",
        kind="correlation",
        settings={"mode": "single"},
        workspace_id="corr",
    )

    updated = manager.update_workspace_settings(project.id, "corr", {"mode": "multi", "layout": "grid"})
    opened = manager.open_workspace(project.id, "corr")

    assert updated.settings == {"mode": "multi", "layout": "grid"}
    assert opened.settings == updated.settings


def test_workspace_manager_ensure_workspace_reuses_existing_record(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    manager = WorkspaceManager(tmp_path)

    first = manager.ensure_project_workspace(project.id, name="Default Workspace", workspace_id="main")
    second = manager.ensure_project_workspace(project.id, name="Changed Name", workspace_id="main")

    assert first.id == "main"
    assert second.id == "main"
    assert second.name == "Default Workspace"
    assert len(manager.list_project_workspaces(project.id)) == 1


def test_workspace_manager_delete_returns_user_facing_status(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    manager = WorkspaceManager(tmp_path)
    manager.create_project_workspace(project.id, "Temporary", workspace_id="tmp")

    deleted = manager.delete_project_workspace(project.id, "tmp")
    missing = manager.delete_project_workspace(project.id, "tmp")

    assert deleted.deleted is True
    assert "deleted" in deleted.message
    assert missing.deleted is False
    assert "not found" in missing.message


def test_workspace_manager_rejects_invalid_workspace_id(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    manager = WorkspaceManager(tmp_path)

    with pytest.raises(ValueError):
        manager.open_workspace(project.id, "bad/path")
