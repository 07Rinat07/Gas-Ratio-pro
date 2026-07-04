from __future__ import annotations

import pandas as pd
import pytest

from projects import (
    list_project_calculations,
    filter_project_calculations,
    read_project_calculation_dataframe,
    read_project_calculation_file_bytes,
    read_project_calculation_metadata,
    save_project_calculation,
    summarize_project_calculations,
)


def test_project_calculation_roundtrip_saves_table_metadata_and_exports(tmp_path):
    df = pd.DataFrame(
        {
            "depth": [1000.0, 1001.0],
            "c1": [80.0, 90.0],
            "wh": [12.5, 13.5],
            "interpretation": ["Газовая залежь", "Недостаточно данных"],
        }
    )

    record = save_project_calculation(
        df,
        root=tmp_path,
        project_id="demo",
        source_label="Project LAS: Well A",
        sheet_name="Well A / prepared",
        mapping={"depth": "DEPT", "c1": "C1"},
        ch_mode="A",
        warnings=("Проверьте C2", "Проверьте C2"),
        header_row=0,
    )

    records = list_project_calculations(tmp_path, "demo")
    loaded_df = read_project_calculation_dataframe(tmp_path, "demo", record.id)
    metadata = read_project_calculation_metadata(tmp_path, "demo", record.id)

    assert len(records) == 1
    assert records[0].id == record.id
    assert records[0].row_count == 2
    assert records[0].warnings_count == 1
    assert loaded_df["depth"].tolist() == [1000.0, 1001.0]
    assert metadata["mapping"] == {"depth": "DEPT", "c1": "C1"}
    assert metadata["warnings"] == ["Проверьте C2"]
    assert metadata["header_row"] == 0
    assert read_project_calculation_file_bytes(tmp_path, "demo", record.id, "csv").startswith(
        bytes([0xEF, 0xBB, 0xBF])
    )
    assert read_project_calculation_file_bytes(tmp_path, "demo", record.id, "xlsx").startswith(b"PK")
    assert (tmp_path / "demo" / "calculations" / record.id / "metadata.json").exists()


def test_project_calculation_uses_unique_ids_and_lists_newest_first(tmp_path):
    df = pd.DataFrame({"depth": [1.0], "c1": [2.0]})

    first = save_project_calculation(df, root=tmp_path, project_id="demo", source_label="same")
    second = save_project_calculation(df, root=tmp_path, project_id="demo", source_label="same")
    records = list_project_calculations(tmp_path, "demo")

    assert first.id != second.id
    assert records[0].id == second.id
    assert {record.id for record in records} == {first.id, second.id}


def test_project_calculation_validates_empty_data_and_unsafe_project_id(tmp_path):
    with pytest.raises(ValueError, match="Нет расчетных данных"):
        save_project_calculation(pd.DataFrame(), root=tmp_path, project_id="demo")

    with pytest.raises(ValueError, match="Некорректный идентификатор проекта"):
        save_project_calculation(pd.DataFrame({"depth": [1.0]}), root=tmp_path, project_id="../bad")


def test_project_calculation_read_rejects_unknown_record_or_file_key(tmp_path):
    df = pd.DataFrame({"depth": [1.0], "c1": [2.0]})
    record = save_project_calculation(df, root=tmp_path, project_id="demo")

    with pytest.raises(FileNotFoundError, match="Project calculation not found"):
        read_project_calculation_file_bytes(tmp_path, "demo", "missing", "csv")

    with pytest.raises(FileNotFoundError, match="Project calculation file not found"):
        read_project_calculation_file_bytes(tmp_path, "demo", record.id, "pdf")


def test_project_calculations_summary_aggregates_records_and_columns(tmp_path):
    first_df = pd.DataFrame({"depth": [1000.0, 1001.0], "c1": [80.0, 90.0], "wh": [1.2, 1.4]})
    second_df = pd.DataFrame({"depth": [1002.0], "c2": [10.0], "bh": [0.4]})

    save_project_calculation(
        first_df,
        root=tmp_path,
        project_id="demo",
        source_label="Well A",
        warnings=("check c2",),
    )
    save_project_calculation(
        second_df,
        root=tmp_path,
        project_id="demo",
        source_label="Well B",
        warnings=("check c3", "check c4"),
    )

    summary = summarize_project_calculations(tmp_path, "demo")

    assert summary.count == 2
    assert summary.total_rows == 3
    assert summary.total_warnings == 3
    assert summary.latest_source_label == "Well B"
    assert summary.sources == ("Well B", "Well A")
    assert set(summary.columns) == {"depth", "c1", "wh", "c2", "bh"}


def test_project_calculations_summary_returns_empty_state(tmp_path):
    summary = summarize_project_calculations(tmp_path, "demo")

    assert summary.count == 0
    assert summary.total_rows == 0
    assert summary.total_warnings == 0
    assert summary.sources == ()
    assert summary.columns == ()


def test_project_calculation_filter_matches_source_warnings_and_columns(tmp_path):
    first_df = pd.DataFrame({"depth": [1000.0], "c1": [80.0], "wh": [1.2]})
    second_df = pd.DataFrame({"depth": [1001.0], "c2": [10.0], "bh": [0.4]})
    third_df = pd.DataFrame({"depth": [1002.0], "c1": [70.0], "c2": [8.0], "pixler_c1_c2": [8.75]})

    save_project_calculation(
        first_df,
        root=tmp_path,
        project_id="demo",
        source_label="Well A gas calculation",
        warnings=("check c2",),
    )
    save_project_calculation(
        second_df,
        root=tmp_path,
        project_id="demo",
        source_label="Well B clean calculation",
        warnings=(),
    )
    save_project_calculation(
        third_df,
        root=tmp_path,
        project_id="demo",
        source_label="Well C Pixler calculation",
        warnings=("check mapping",),
    )

    by_source = filter_project_calculations(tmp_path, "demo", source_query="well b")
    with_warnings = filter_project_calculations(tmp_path, "demo", warning_state="with_warnings")
    without_warnings = filter_project_calculations(tmp_path, "demo", warning_state="without_warnings")
    with_columns = filter_project_calculations(tmp_path, "demo", required_columns=("depth", "c1", "c2"))
    combined = filter_project_calculations(
        tmp_path,
        "demo",
        source_query="pixler",
        warning_state="with_warnings",
        required_columns=("pixler_c1_c2",),
    )

    assert [record.source_label for record in by_source] == ["Well B clean calculation"]
    assert {record.source_label for record in with_warnings} == {
        "Well A gas calculation",
        "Well C Pixler calculation",
    }
    assert [record.source_label for record in without_warnings] == ["Well B clean calculation"]
    assert [record.source_label for record in with_columns] == ["Well C Pixler calculation"]
    assert [record.source_label for record in combined] == ["Well C Pixler calculation"]


def test_project_calculation_filter_rejects_unknown_warning_state(tmp_path):
    save_project_calculation(
        pd.DataFrame({"depth": [1.0], "c1": [2.0]}),
        root=tmp_path,
        project_id="demo",
    )

    with pytest.raises(ValueError, match="Некорректный режим"):
        filter_project_calculations(tmp_path, "demo", warning_state="broken")
