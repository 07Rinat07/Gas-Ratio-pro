from __future__ import annotations

import pandas as pd
import pytest

from projects import (
    list_project_calculations,
    read_project_calculation_dataframe,
    read_project_calculation_file_bytes,
    read_project_calculation_metadata,
    save_project_calculation,
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
