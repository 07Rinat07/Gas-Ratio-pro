from __future__ import annotations

import importlib

import pandas as pd


def test_streamlit_app_imports():
    module = importlib.import_module("app.streamlit_app")

    assert hasattr(module, "main")


def test_las_editor_helpers_prepare_raw_sheet_for_workspace():
    module = importlib.import_module("app.streamlit_app")
    df = pd.DataFrame({"DEPT": [1.2, 1.4], "C1": [80, 90]})

    raw_sheet = module._dataframe_to_raw_sheet(df)

    assert module._find_default_depth_column(df) == "DEPT"
    assert list(raw_sheet.iloc[0]) == ["DEPT", "C1"]
    assert raw_sheet.iloc[1, 0] == 1.2
