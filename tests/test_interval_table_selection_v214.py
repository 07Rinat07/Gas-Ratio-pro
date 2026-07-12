from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.streamlit_app import (
    _selected_dataframe_rows,
    _selected_interval_id_from_table,
)


def test_selected_interval_id_is_read_from_dataframe_event() -> None:
    event = {"selection": {"rows": [1]}}
    table = pd.DataFrame({"ID": ["HC-001", "HC-022"]})
    assert _selected_dataframe_rows(event) == [1]
    assert _selected_interval_id_from_table(event, table) == "HC-022"


def test_engineering_tables_drive_shared_selection_without_selectbox() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'key="workspace_engineering_interval_table"' in source
    assert 'key="interpretation_engineering_interval_table"' in source
    assert 'on_select="rerun"' in source
    assert 'selection_mode="single-row"' in source
    assert '"selected_reservoir_interval_id": table_interval_id' in source
    assert '"Выбранный пласт для Pixler и ternary"' not in source
    assert '"Выбранный пласт / интервал"' not in source
