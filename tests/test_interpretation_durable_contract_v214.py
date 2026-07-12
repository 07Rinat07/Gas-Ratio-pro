from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from core.session_state_manager import clear_on_workspace_change


def test_durable_active_calculation_survives_workspace_cleanup() -> None:
    frame = pd.DataFrame({"depth": [1.0, 2.0], "Wh": [1.2, 1.3]})
    state = {
        "active_project_id": "default",
        "active_workspace_id": "nav.data",
        "workbench_active_calculation": {
            "project_id": "default",
            "source": "well.las",
            "rows": 2,
            "calculation_revision": 1,
            "dataframe": frame,
        },
        "interpretation_session_data": frame,
        "interpretation_figure_cache": {"old": True},
    }

    result = clear_on_workspace_change(state, "default", "", "", "nav.interpretation")

    assert "interpretation_session_data" in result.cleared_keys
    assert "interpretation_figure_cache" in result.cleared_keys
    assert "workbench_active_calculation" in state
    assert state["workbench_active_calculation"]["dataframe"].equals(frame)


def test_streamlit_app_contains_durable_calculation_contract() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'ACTIVE_CALCULATION_CONTRACT_KEY = "workbench_active_calculation"' in source
    assert '"active_calculation_committed project_id=%s rows=%d revision=%d source=%s"' in source
    assert '"active_calculation_restored project_id=%s rows=%d revision=%s"' in source
    assert "ACTIVE_CALCULATION_CONTRACT_KEY: durable_contract" in source
