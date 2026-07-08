from __future__ import annotations

import pytest

from core.application_state import ACTIVE_WORKSPACE_ID_KEY
from projects.repository import create_project
from projects.workspace_controller import WorkspaceController


def test_workspace_controller_creates_and_activates_workspace(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {}
    controller = WorkspaceController(state, tmp_path)

    result = controller.create_workspace(
        project.id,
        "LAS Workspace",
        kind="las",
        workspace_id="las-main",
        settings={"depth_unit": "m"},
    )

    assert result.created is True
    assert result.workspace.id == "las-main"
    assert result.transition.changed is True
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "las-main"
    assert controller.list_project_workspaces(project.id)[0].is_active is True


def test_workspace_controller_opens_existing_workspace_through_state_boundary(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {ACTIVE_WORKSPACE_ID_KEY: "old"}
    controller = WorkspaceController(state, tmp_path)
    controller.create_workspace(project.id, "Correlation", kind="correlation", workspace_id="corr", activate=False)

    opened = controller.open_workspace(project.id, "corr")

    assert opened.created is False
    assert opened.workspace.kind == "correlation"
    assert opened.transition.before.workspace_id == "old"
    assert opened.transition.after.workspace_id == "corr"
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "corr"


def test_workspace_controller_ensures_active_workspace_when_missing(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {}
    controller = WorkspaceController(state, tmp_path)

    ensured = controller.ensure_active_workspace(
        project.id,
        name="Default Workspace",
        workspace_id="main",
    )
    reused = controller.ensure_active_workspace(project.id, workspace_id="main")

    assert ensured.created is True
    assert reused.created is False
    assert reused.workspace.id == "main"
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "main"


def test_workspace_controller_updates_active_workspace_settings(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {}
    controller = WorkspaceController(state, tmp_path)
    controller.create_workspace(project.id, "Petrophysics", workspace_id="petro", settings={"track": "GR"})

    updated = controller.update_active_workspace_settings(project.id, {"track": "RHOB", "layout": "grid"})

    assert updated.settings == {"track": "RHOB", "layout": "grid"}


def test_workspace_controller_rejects_settings_update_without_active_workspace(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    controller = WorkspaceController({}, tmp_path)

    with pytest.raises(ValueError):
        controller.update_active_workspace_settings(project.id, {"track": "GR"})


def test_workspace_controller_deletes_active_workspace_and_clears_context(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {}
    controller = WorkspaceController(state, tmp_path)
    controller.create_workspace(project.id, "Temporary", workspace_id="tmp")

    deleted = controller.delete_workspace(project.id, "tmp")

    assert deleted.delete_result.deleted is True
    assert deleted.transition is not None
    assert state[ACTIVE_WORKSPACE_ID_KEY] == ""
    assert controller.list_project_workspaces(project.id) == ()
