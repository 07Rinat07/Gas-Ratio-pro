from pathlib import Path

import pytest

from core.application_state import (
    ACTIVE_LAS_ID_KEY,
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    PENDING_ACTIVE_PROJECT_ID_KEY,
    ApplicationStateController,
)
from projects.repository import DEFAULT_PROJECT_ID, create_project, delete_project, ensure_default_project, list_projects
from wells.repository import delete_well_record, delete_well_version, list_wells, save_well_version

import pandas as pd


def test_application_state_switch_project_clears_derived_tables_and_keeps_context():
    state = {
        ACTIVE_PROJECT_ID_KEY: "old-project",
        "active_workspace_id": "las_workspace",
        "las_editor_session_sheets": {"LAS": [["DEPT"], [1000.0]]},
        "dashboard_metrics": {"rows": 1},
        "active_validation_table": [{"status": "old"}],
        "user_settings": {"theme": "dark"},
    }

    transition = ApplicationStateController(state).activate_project("new-project")

    assert transition.changed is True
    assert state[ACTIVE_PROJECT_ID_KEY] == "new-project"
    assert state[ACTIVE_WELL_ID_KEY] == ""
    assert state[ACTIVE_LAS_ID_KEY] == ""
    assert "las_editor_session_sheets" not in state
    assert "dashboard_metrics" not in state
    assert "active_validation_table" not in state
    assert state["user_settings"] == {"theme": "dark"}
    assert transition.cleanup is not None
    assert "las_editor_session_sheets" in transition.cleanup.cleared_keys


def test_pending_project_activation_is_applied_before_widgets_render():
    state = {ACTIVE_PROJECT_ID_KEY: "old-project", "table_preview": [1, 2, 3]}
    controller = ApplicationStateController(state)

    controller.request_project_activation("created-project")
    assert state[PENDING_ACTIVE_PROJECT_ID_KEY] == "created-project"

    transition = controller.consume_pending_project_activation()

    assert transition is not None
    assert transition.changed is True
    assert state[ACTIVE_PROJECT_ID_KEY] == "created-project"
    assert PENDING_ACTIVE_PROJECT_ID_KEY not in state
    assert "table_preview" not in state


def test_delete_project_removes_persistent_project_directory(tmp_path: Path):
    ensure_default_project(tmp_path)
    project = create_project(tmp_path, name="Demo")

    assert (tmp_path / project.id / "project.json").exists()
    assert delete_project(tmp_path, project.id) is True
    assert project.id not in {item.id for item in list_projects(tmp_path)}
    assert not (tmp_path / project.id).exists()

    with pytest.raises(ValueError):
        delete_project(tmp_path, DEFAULT_PROJECT_ID)


def test_delete_well_record_removes_manifest_and_versions(tmp_path: Path):
    df = pd.DataFrame({"DEPT": [1000.0, 1000.5], "GR": [80.0, 82.0]})
    record = save_well_version(df, root=tmp_path, well_name="Well A", depth_column="DEPT")

    assert (tmp_path / record.id / "manifest.json").exists()
    assert delete_well_record(tmp_path, record.id) is True
    assert list_wells(tmp_path) == ()
    assert not (tmp_path / record.id).exists()


def test_delete_well_version_updates_manifest_without_restoring_deleted_data(tmp_path: Path):
    df = pd.DataFrame({"DEPT": [1.0, 2.0], "GR": [10.0, 11.0]})
    record = save_well_version(df, root=tmp_path, well_name="Well B", version_label="v1", depth_column="DEPT")
    record = save_well_version(df, root=tmp_path, well_id=record.id, version_label="v2", depth_column="DEPT")
    deleted_version = record.versions[0].id

    updated = delete_well_version(tmp_path, record.id, deleted_version)

    assert deleted_version not in {version.id for version in updated.versions}
    assert not (tmp_path / record.id / "versions" / deleted_version).exists()
    assert len(updated.versions) == 1


def test_application_state_controller_manages_application_values():
    state = {}
    controller = ApplicationStateController(state)

    controller.set_value("interpretation_session_source", "LAS")
    controller.update_values({"table_preview": [1, 2], "active_summary_table": {"rows": 2}})

    assert controller.get_value("interpretation_session_source") == "LAS"
    assert controller.get_value("missing", "fallback") == "fallback"
    assert state["table_preview"] == [1, 2]
    assert state["active_summary_table"] == {"rows": 2}
