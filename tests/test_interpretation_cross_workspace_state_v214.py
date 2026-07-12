from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.session_state_manager import clear_on_project_change, clear_on_workspace_change


ACTIVE_DATA = "active_calculation_result_data"
ACTIVE_SOURCE = "active_calculation_result_source"
ACTIVE_PROJECT = "active_calculation_project_id"


def test_committed_calculation_survives_workspace_navigation() -> None:
    frame = pd.DataFrame({"depth": [1000.0], "wh": [1.2]})
    state: dict[str, object] = {
        "active_project_id": "default",
        "active_workspace_id": "data",
        "interpretation_session_data": frame,
        ACTIVE_DATA: frame,
        ACTIVE_SOURCE: "LAS",
        ACTIVE_PROJECT: "default",
    }

    clear_on_workspace_change(state, "default", "", "", "interpretation")

    # Legacy workspace-local data may be cleared, but the committed inter-module
    # result must remain available to Interpretation and Reports.
    assert "interpretation_session_data" not in state
    assert state[ACTIVE_DATA] is frame
    assert state[ACTIVE_SOURCE] == "LAS"
    assert state[ACTIVE_PROJECT] == "default"


def test_project_change_cannot_reuse_committed_calculation_from_another_project() -> None:
    frame = pd.DataFrame({"depth": [1000.0], "wh": [1.2]})
    state: dict[str, object] = {
        "active_project_id": "default",
        ACTIVE_DATA: frame,
        ACTIVE_SOURCE: "LAS",
        ACTIVE_PROJECT: "default",
    }

    clear_on_project_change(state, "other-project")

    # The application-level reader additionally checks ACTIVE_PROJECT against
    # the requested project, so a result from "default" cannot be displayed in
    # "other-project" even though the durable value survives generic cleanup.
    assert state[ACTIVE_PROJECT] == "default"
    assert state["active_project_id"] == "other-project"


def test_interpretation_and_reports_read_shared_active_calculation_contract() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'ACTIVE_CALCULATION_DATA_KEY = "active_calculation_result_data"' in source
    assert "def _active_calculation_dataset(" in source
    assert "calculated_df, source_label = _active_calculation_dataset(active_project.id)" in source
    assert "calculated_df, _source_label = _active_calculation_dataset(active_project.id)" in source
    assert "interpretation_data_unavailable" in source
