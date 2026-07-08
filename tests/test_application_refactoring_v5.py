from pathlib import Path
import importlib

import pytest

from core.integration_audit import audit_streamlit_app, scan_session_state_access

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
    assert controller.ensure_value("las_editor_curve_alias_history", ()) == ()
    assert controller.get_list("table_preview") == [1, 2]
    assert controller.get_tuple("table_preview") == (1, 2)
    assert controller.get_dict("active_summary_table") == {"rows": 2}
    assert state["table_preview"] == [1, 2]
    assert state["active_summary_table"] == {"rows": 2}


def test_command_palette_state_helpers_use_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    remember_body = inspect.getsource(module._remember_command_palette_entry)
    toggle_body = inspect.getsource(module._toggle_command_palette_favorite)

    assert "_application_state_controller()" in remember_body
    assert "_application_state_controller()" in toggle_body
    assert "st.session_state" not in remember_body
    assert "st.session_state" not in toggle_body


def test_navigation_and_workflow_helpers_use_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    workflow_body = inspect.getsource(module._workflow_status_detail_rows)
    set_tab_body = inspect.getsource(module._set_active_main_tab)
    active_tab_body = inspect.getsource(module._active_main_tab)
    quick_action_body = inspect.getsource(module._trigger_quick_action)

    assert "_application_state_controller()" in workflow_body
    assert "st.session_state" not in workflow_body
    assert "_application_state_controller()" in set_tab_body
    assert "st.session_state" not in set_tab_body
    assert "_application_state_controller()" in active_tab_body
    assert "st.session_state" not in active_tab_body
    assert "_application_state_controller()" in quick_action_body
    assert "st.session_state" not in quick_action_body


def test_interpretation_and_correlation_settings_helpers_use_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    helper_names = (
        "_set_interpretation_x_range_state",
        "_set_tablet_x_range_state",
        "_apply_interpretation_graph_settings_to_session",
        "_set_las_correlation_x_range_state",
        "_apply_las_correlation_settings_to_session",
    )

    for helper_name in helper_names:
        helper_body = inspect.getsource(getattr(module, helper_name))
        assert "_application_state_controller()" in helper_body or helper_name == "_set_tablet_x_range_state"
        assert "st.session_state" not in helper_body


def test_application_state_controller_clear_matching_removes_owned_keys():
    state = {
        "las_editor_session_sheets": {"LAS": []},
        "graph_settings": {"x": 1},
        "user_settings": {"theme": "dark"},
    }
    controller = ApplicationStateController(state)

    removed = controller.clear_matching(
        exact_keys={"las_editor_session_sheets"},
        prefixes=("graph_",),
    )

    assert set(removed) == {"las_editor_session_sheets", "graph_settings"}
    assert state == {"user_settings": {"theme": "dark"}}


def test_las_editor_session_state_helpers_use_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    clear_body = inspect.getsource(module._clear_las_working_state)
    new_las_body = inspect.getsource(module._render_new_las_creator_panel)
    saved_wells_body = inspect.getsource(module._render_saved_wells_panel)

    assert "clear_matching" in clear_body
    assert "st.session_state" not in clear_body
    assert "_application_state_controller().update_values" in new_las_body
    assert "st.session_state" not in new_las_body
    assert "_application_state_controller().update_values" in saved_wells_body
    assert "st.session_state" not in saved_wells_body


def test_interpretation_tablet_state_helpers_use_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    helper_names = (
        "_tablet_columns_state",
        "_apply_mud_gas_tablet_preset_to_state",
        "_apply_mud_gas_tablet_markers_to_state",
        "_tablet_fill_mode_default",
    )

    for helper_name in helper_names:
        helper_body = inspect.getsource(getattr(module, helper_name))
        assert "_application_state_controller()" in helper_body
        assert "st.session_state" not in helper_body


def test_las_correlation_settings_ui_uses_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    helper_names = (
        "_render_las_correlation_settings_loader",
        "_render_las_correlation_settings_saver",
    )

    for helper_name in helper_names:
        helper_body = inspect.getsource(getattr(module, helper_name))
        assert "_application_state_controller()" in helper_body
        assert "st.session_state" not in helper_body


def test_start_tab_reads_layout_through_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    helper_body = inspect.getsource(module._render_start_tab)
    assert "_application_state_controller().get_value" in helper_body
    assert "st.session_state" not in helper_body


def test_las_correlation_studio_state_uses_application_state_controller():
    module = importlib.import_module("app.streamlit_app")
    import inspect

    helper_body = inspect.getsource(module._render_las_correlation_tab)
    assert 'state_controller.get_value(\n            "las_correlation_studio_markers"' in helper_body
    assert 'state_controller.set_value("las_correlation_studio_markers"' in helper_body
    assert 'state_controller.get_value("las_correlation_comparison_curve")' in helper_body
    assert 'state_controller.set_value("las_correlation_comparison_curve"' in helper_body


def test_final_streamlit_state_audit_allows_only_controller_factory():
    app_path = Path("app/streamlit_app.py")

    findings = scan_session_state_access(app_path, Path("."))

    assert findings == ()


def test_integration_audit_has_no_application_state_boundary_errors():
    report = audit_streamlit_app(Path("."))

    assert not [
        finding
        for finding in report.errors
        if finding.detail == "direct st.session_state access outside ApplicationStateController boundary"
    ]
