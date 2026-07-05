from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd


def test_streamlit_app_imports():
    module = importlib.import_module("app.streamlit_app")

    assert hasattr(module, "main")


def test_streamlit_app_exposes_expected_tabs():
    module = importlib.import_module("app.streamlit_app")

    assert "LAS-корреляция" in module.APP_TABS
    assert "Интерпретационные графики" in module.APP_TABS
    assert module.TABLET_TRACK_OPTION in module.INTERPRETATION_TRACK_OPTIONS
    assert hasattr(module, "_render_las_correlation_tab")


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


def test_streamlit_app_documentation_docs_include_project_plan():
    module = importlib.import_module("app.streamlit_app")
    doc_paths = {path for _title, path in module.DOCUMENTATION_TAB_DOCS}

    assert "docs/project_plan.md" in doc_paths
    assert "docs/user_guide.md" in doc_paths
    assert "docs/troubleshooting.md" in doc_paths


def test_selected_interval_rule_messages_explain_nan():
    module = importlib.import_module("app.streamlit_app")
    row = pd.Series({"interpretation": "Недостаточно данных", "wh": float("nan"), "bh": float("nan")})

    messages = module._selected_interval_rule_messages(row)

    assert any("Wh/Bh неполные" in message for message in messages)
    assert any("mapping" in message for message in messages)

def test_las_correlation_report_rows_include_print_context():
    module = importlib.import_module("app.streamlit_app")
    project = module.ProjectRecord(id="default", name="Основной проект")

    class WellStub:
        def __init__(self, name: str):
            self.name = name

    rows = dict(
        module._las_correlation_report_rows(
            project=project,
            selected_wells=(WellStub("Well A"), WellStub("Well B")),
            depth_range=(1000.0, 1005.0),
            gis_groups=("gamma",),
            gas_groups=("total_gas",),
            gis_x_range=(0.0, 150.0),
            gas_x_range=None,
            view_mode=module.VIEW_MODE_BY_CURVE,
            comparison_curve="GR",
        )
    )

    assert rows["Проект"] == "Основной проект (default)"
    assert rows["Скважины"] == "Well A, Well B"
    assert rows["Интервал глубины"] == "1000-1005 м"
    assert rows["Представление"] == module.VIEW_MODE_BY_CURVE
    assert rows["Кривая сравнения"] == "GR"
    assert rows["X-scale ГИС"] == "0-150"
    assert "Дата выгрузки" in rows


def test_project_las_records_to_raw_sheets_loads_project_version(monkeypatch, tmp_path):
    module = importlib.import_module("app.streamlit_app")
    sample = Path("examples/sample_gas_data.las").read_bytes()
    record = module.save_project_las_file(
        sample,
        root=tmp_path,
        project_id="demo",
        file_name="well_a.las",
        well_name="Well A",
        version_label="prepared",
    )
    monkeypatch.setattr(module, "LAS_CORRELATION_PROJECTS_ROOT", tmp_path)

    sheets = module._project_las_records_to_raw_sheets(
        module.ProjectRecord(id="demo", name="Demo"),
        (record,),
    )

    assert list(sheets) == ["Well A / prepared"]
    assert list(sheets["Well A / prepared"].iloc[0])[:2] == ["DEPT", "C1"]



def test_start_screen_actions_cover_main_workflows():
    module = importlib.import_module("app.streamlit_app")

    assert module.APP_TABS[0] == "Старт"
    assert module._start_action_titles() == (
        "Загрузить данные",
        "Открыть LAS-редактор",
        "Открыть корреляцию",
        "Открыть интерпретационные графики",
        "Открыть документацию",
    )


def test_workflow_status_rows_explain_empty_session(monkeypatch):
    module = importlib.import_module("app.streamlit_app")
    monkeypatch.setattr(module.st, "session_state", {})

    rows = dict(module._workflow_status_rows(module.ProjectRecord(id="demo", name="Demo")))

    assert rows["Активный проект"] == "Demo (demo)"
    assert "не загружены" in rows["LAS-редактор"]
    assert "сначала выполните расчет" in rows["Интерпретационные графики"]


def test_workflow_status_detail_rows_include_next_actions(monkeypatch):
    module = importlib.import_module("app.streamlit_app")
    monkeypatch.setattr(module.st, "session_state", {})

    rows = module._workflow_status_detail_rows(module.ProjectRecord(id="demo", name="Demo"))

    assert all(len(row) == 3 for row in rows)
    assert any("Дальше" not in action and action for _label, _status, action in rows)
    assert rows[0][0] == "Активный проект"


def test_dataframe_shape_label_for_ui_tables():
    module = importlib.import_module("app.streamlit_app")

    assert module._dataframe_shape_label(pd.DataFrame({"A": [1, 2], "B": [3, 4]})) == "строк: 2, колонок: 2"
    assert module._dataframe_shape_label(None) == "нет данных"


def test_layout_profile_options_cover_standard_and_wide():
    module = importlib.import_module("app.streamlit_app")

    assert module._layout_profile_options() == ("Телефон", "Ноутбук", "Большой экран")
    assert module._layout_profile_key("Телефон") == "phone"
    assert module._layout_profile_key("Ноутбук") == "standard"
    assert module._layout_profile_key("Большой экран") == "wide"
    assert module._layout_profile_key("unknown") == "wide"


def test_layout_profile_summary_explains_screen_mode():
    module = importlib.import_module("app.streamlit_app")

    label, max_width, description = module._layout_profile_summary("standard")

    assert label == "Ноутбук"
    assert "1440px" in max_width
    assert "стандартных экранов" in description or "ноутбуков" in description.lower()


def test_project_workspace_summary_counts_versions_archives_and_exports(monkeypatch, tmp_path):
    module = importlib.import_module("app.streamlit_app")
    sample = Path("examples/sample_gas_data.las").read_bytes()
    first = module.save_project_las_file(
        sample,
        root=tmp_path,
        project_id="demo",
        file_name="well_a.las",
        well_name="Well A",
        version_label="raw",
    )
    module.save_project_las_file(
        sample,
        root=tmp_path,
        project_id="demo",
        file_name="well_b.las",
        well_name="Well B",
        version_label="prepared",
    )
    module.set_project_las_file_archived(tmp_path, "demo", first.id, archived=True)
    module.save_project_export(
        b"depth,c1\n1000,10\n",
        root=tmp_path,
        project_id="demo",
        label="Interval CSV",
        file_name="interval.csv",
        kind="csv",
    )
    monkeypatch.setattr(module, "LAS_CORRELATION_PROJECTS_ROOT", tmp_path)

    rows = dict(module._project_workspace_summary_rows(module.ProjectRecord(id="demo", name="Demo")))

    assert rows["Скважин"] == "2"
    assert rows["LAS-версий"] == "2"
    assert rows["Активных LAS-версий"] == "1"
    assert rows["Архивных LAS-версий"] == "1"
    assert rows["Доступных экспортов"] == "1"
