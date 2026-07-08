from __future__ import annotations

from core.application_state import ACTIVE_WORKSPACE_ID_KEY
from projects.repository import create_project
from projects.workspace_controller import WorkspaceController


def test_workspace_lifecycle_switch_clears_workspace_local_state(tmp_path):
    """Opening another workspace must clear derived workspace/UI artifacts."""

    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {
        ACTIVE_WORKSPACE_ID_KEY: "first",
        "workspace_local_selection": "curve-a",
        "curve_table_preview": [1, 2, 3],
        "user_settings": {"theme": "dark"},
    }
    controller = WorkspaceController(state, tmp_path)
    controller.create_workspace(project.id, "First", workspace_id="first", activate=False)
    controller.create_workspace(project.id, "Second", workspace_id="second", activate=False)

    opened = controller.open_workspace(project.id, "second")

    assert opened.transition.changed is True
    assert opened.transition.cleanup is not None
    assert opened.transition.cleanup.reason == "workspace_changed"
    assert "workspace_local_selection" in opened.transition.cleanup.cleared_keys
    assert "curve_table_preview" in opened.transition.cleanup.cleared_keys
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "second"
    assert state["user_settings"] == {"theme": "dark"}


def test_workspace_lifecycle_create_without_activation_does_not_clear_ui_state(tmp_path):
    """Creating a background workspace should not invalidate current UI state."""

    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {
        ACTIVE_WORKSPACE_ID_KEY: "current",
        "workspace_local_selection": "curve-a",
    }
    controller = WorkspaceController(state, tmp_path)

    created = controller.create_workspace(project.id, "Background", workspace_id="background", activate=False)

    assert created.created is True
    assert created.transition.changed is False
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "current"
    assert state["workspace_local_selection"] == "curve-a"


def test_workspace_lifecycle_close_clears_active_workspace_only(tmp_path):
    """Closing workspace clears active workspace context through ApplicationStateController."""

    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {
        ACTIVE_WORKSPACE_ID_KEY: "active",
        "workspace_local_filter": "GR",
    }
    controller = WorkspaceController(state, tmp_path)
    controller.create_workspace(project.id, "Active", workspace_id="active", activate=False)

    transition = controller.close_workspace()

    assert transition.changed is True
    assert transition.cleanup is not None
    assert transition.cleanup.reason == "workspace_changed"
    assert state[ACTIVE_WORKSPACE_ID_KEY] == ""
    assert "workspace_local_filter" not in state


def test_workspace_lifecycle_delete_inactive_workspace_keeps_active_context(tmp_path):
    """Deleting an inactive workspace must not close another active workspace."""

    project = create_project(tmp_path, name="Demo Project", project_id="demo")
    state = {ACTIVE_WORKSPACE_ID_KEY: "active"}
    controller = WorkspaceController(state, tmp_path)
    controller.create_workspace(project.id, "Active", workspace_id="active", activate=False)
    controller.create_workspace(project.id, "Inactive", workspace_id="inactive", activate=False)

    deleted = controller.delete_workspace(project.id, "inactive")

    assert deleted.delete_result.deleted is True
    assert deleted.transition is None
    assert state[ACTIVE_WORKSPACE_ID_KEY] == "active"
    assert tuple(item.id for item in controller.list_project_workspaces(project.id)) == ("active",)
