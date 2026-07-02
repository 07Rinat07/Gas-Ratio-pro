from __future__ import annotations

import importlib
from pathlib import Path

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

class _UploadedFileStub:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self.size = len(data)
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def test_multi_file_loader_prefixes_las_sheet_names():
    module = importlib.import_module("app.streamlit_app")
    sample = Path("examples/sample_gas_data.las").read_bytes()

    sheets = module._load_uploaded_files_sheets(
        [
            _UploadedFileStub("well_a.las", sample),
            _UploadedFileStub("well_b.las", sample),
        ]
    )

    assert list(sheets) == ["well_a / LAS", "well_b / LAS"]
    assert list(sheets["well_a / LAS"].iloc[0])[:2] == ["DEPT", "C1"]


def test_filter_by_depth_range_keeps_selected_interval():
    module = importlib.import_module("app.streamlit_app")
    df = pd.DataFrame({"depth": [1000.0, 1001.0, 1002.0], "c1": [1, 2, 3]})

    filtered = module._filter_by_depth_range(df, 1000.5, 1002.0)

    assert list(filtered["depth"]) == [1001.0, 1002.0]

def test_store_interpretation_dataset_updates_session_state(monkeypatch):
    module = importlib.import_module("app.streamlit_app")
    session_state = {}
    monkeypatch.setattr(module.st, "session_state", session_state)
    df = pd.DataFrame({"depth": [1000.0], "interpretation": ["Газовая залежь"]})

    module._store_interpretation_dataset(df, "LAS")

    assert session_state[module.INTERPRETATION_SESSION_DATA_KEY].equals(df)
    assert session_state[module.INTERPRETATION_SESSION_SOURCE_KEY] == "LAS"
