from __future__ import annotations

import pandas as pd
import pytest

from projects import (
    build_project_dataset_table,
    build_project_las_dataset_record,
    list_project_las_datasets,
    save_project_las_file,
)

LAS_BYTES = b"~Version\nVERS. 2.0\n~Curve\nDEPT.M : Depth\nGR.API : Gamma\nC1.PCT : Methane\n~ASCII\n1000 45 1.2\n1001 46 1.3\n"
NO_DEPTH_LAS_BYTES = b"~Version\nVERS. 2.0\n~Curve\nGR.API : Gamma\nC1.PCT : Methane\n~ASCII\n45 1.2\n46 1.3\n"


def test_project_las_dataset_manager_indexes_saved_las(tmp_path):
    record = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
        version_label="raw",
    )

    datasets = list_project_las_datasets(tmp_path, "demo")

    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset.id == f"las:{record.id}"
    assert dataset.kind == "LAS"
    assert dataset.source_id == record.id
    assert dataset.well_id == "well-a"
    assert dataset.row_count == 2
    assert dataset.column_count == 3
    assert dataset.depth_curve == "DEPT"
    assert dataset.curves == ("DEPT", "GR", "C1")
    assert dataset.status == "ready"
    assert dataset.warnings == ()


def test_project_las_dataset_manager_flags_missing_depth_curve(tmp_path):
    save_project_las_file(
        NO_DEPTH_LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="No Depth.las",
        well_name="Well B",
    )

    dataset = list_project_las_datasets(tmp_path, "demo")[0]

    assert dataset.status == "warning"
    assert dataset.depth_curve == ""
    assert "Не найдена глубинная кривая DEPT/DEPTH/MD." in dataset.warnings


def test_project_las_dataset_table_contains_compact_summary(tmp_path):
    save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
        version_label="raw",
    )

    table = build_project_dataset_table(list_project_las_datasets(tmp_path, "demo"))

    assert list(table.columns) == [
        "Тип",
        "Dataset",
        "Статус",
        "Скважина ID",
        "Источник ID",
        "Файл",
        "Строк",
        "Кривых",
        "Глубина",
        "Кривые",
        "Предупреждения",
        "Сохранено",
        "Архивировано",
    ]
    assert table.loc[0, "Тип"] == "LAS"
    assert table.loc[0, "Статус"] == "готов"
    assert table.loc[0, "Глубина"] == "DEPT"
    assert "GR" in table.loc[0, "Кривые"]


def test_project_las_dataset_record_can_report_parser_error():
    class DummyRecord:
        id = "bad"
        name = "Broken"
        well_id = "broken"
        version_label = "raw"
        original_file_name = "broken.las"
        saved_at = "2026-01-01T00:00:00Z"
        archived_at = ""
        metadata = {}

    dataset = build_project_las_dataset_record(DummyRecord(), error="Не удалось прочитать LAS")

    assert dataset.status == "error"
    assert dataset.status_label == "ошибка чтения"
    assert dataset.row_count == 0
    assert dataset.warnings == ("Не удалось прочитать LAS",)


def test_project_las_dataset_record_without_dataframe_is_warning(tmp_path):
    record = save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
    )

    dataset = build_project_las_dataset_record(record, dataframe=None)

    assert dataset.status == "warning"
    assert "Таблица LAS не передана" in dataset.warnings[0]

CSV_BYTES = b"Depth,C1,C2\n1000,1.2,0.4\n1001,1.3,0.5\n"
NO_DEPTH_CSV_BYTES = b"Time,C1,C2\n00:00,1.2,0.4\n00:01,1.3,0.5\n"


def test_project_csv_dataset_manager_indexes_saved_csv(tmp_path):
    from projects import list_project_csv_datasets, read_project_csv_dataset_dataframe, save_project_csv_dataset

    record = save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.csv",
        name="Well A gas",
        well_id="well-a",
    )

    datasets = list_project_csv_datasets(tmp_path, "demo")

    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset.id == f"csv:{record.id}"
    assert dataset.kind == "CSV"
    assert dataset.name == "Well A gas"
    assert dataset.source_id == record.id
    assert dataset.well_id == "well-a"
    assert dataset.row_count == 2
    assert dataset.column_count == 3
    assert dataset.depth_curve == "Depth"
    assert dataset.curves == ("Depth", "C1", "C2")
    assert dataset.status == "ready"
    assert dataset.warnings == ()

    dataframe = read_project_csv_dataset_dataframe(tmp_path, "demo", record.id)
    assert list(dataframe.columns) == ["Depth", "C1", "C2"]


def test_project_csv_dataset_manager_flags_missing_depth_column(tmp_path):
    from projects import list_project_csv_datasets, save_project_csv_dataset

    save_project_csv_dataset(
        NO_DEPTH_CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="No Depth.csv",
        name="No depth gas",
    )

    dataset = list_project_csv_datasets(tmp_path, "demo")[0]

    assert dataset.status == "warning"
    assert dataset.depth_curve == ""
    assert "Не найдена глубинная колонка DEPT/DEPTH/MD." in dataset.warnings


def test_project_dataset_table_accepts_las_and_csv_records(tmp_path):
    from projects import build_project_dataset_table, list_project_csv_datasets, save_project_csv_dataset

    save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
        version_label="raw",
    )
    save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.csv",
        name="Well A gas",
        well_id="well-a",
    )

    table = build_project_dataset_table(
        (*list_project_las_datasets(tmp_path, "demo"), *list_project_csv_datasets(tmp_path, "demo"))
    )

    assert set(table["Тип"]) == {"LAS", "CSV"}
    assert "Well A gas" in set(table["Dataset"])
    assert "Depth" in set(table["Глубина"])


def test_project_csv_dataset_duplicate_names_get_unique_ids(tmp_path):
    from projects import save_project_csv_dataset

    first = save_project_csv_dataset(CSV_BYTES, root=tmp_path, project_id="demo", file_name="gas.csv", name="Gas")
    second = save_project_csv_dataset(CSV_BYTES, root=tmp_path, project_id="demo", file_name="gas.csv", name="Gas")

    assert first.id != second.id
    assert second.id.endswith("-2")


def test_project_csv_dataset_rejects_empty_bytes(tmp_path):
    from projects import save_project_csv_dataset

    with pytest.raises(ValueError):
        save_project_csv_dataset(b"", root=tmp_path, project_id="demo")


def _excel_bytes(*, depth_column: str = "MD") -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({depth_column: [1000, 1001], "C1": [1.2, 1.3], "C2": [0.4, 0.5]}).to_excel(
            writer,
            sheet_name="Gas",
            index=False,
        )
        pd.DataFrame({"Name": ["A"], "Value": [1]}).to_excel(writer, sheet_name="Meta", index=False)
    return buffer.getvalue()


def test_project_excel_dataset_manager_indexes_saved_workbook(tmp_path):
    from projects import list_project_excel_datasets, read_project_excel_dataset_dataframe, save_project_excel_dataset

    record = save_project_excel_dataset(
        _excel_bytes(),
        root=tmp_path,
        project_id="demo",
        file_name="Well A.xlsx",
        name="Well A workbook",
        well_id="well-a",
        active_sheet="Gas",
    )

    datasets = list_project_excel_datasets(tmp_path, "demo")

    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset.id == f"excel:{record.id}"
    assert dataset.kind == "Excel"
    assert dataset.name == "Well A workbook"
    assert dataset.source_id == record.id
    assert dataset.well_id == "well-a"
    assert dataset.version_label == "Gas"
    assert dataset.row_count == 2
    assert dataset.column_count == 3
    assert dataset.depth_curve == "MD"
    assert dataset.curves == ("MD", "C1", "C2")
    assert dataset.status == "ready"
    assert dataset.warnings == ()
    assert dataset.metadata["sheet_count"] == 2
    assert dataset.metadata["active_sheet"] == "Gas"
    assert dataset.metadata["sheet_names"] == ["Gas", "Meta"]

    dataframe = read_project_excel_dataset_dataframe(tmp_path, "demo", record.id)
    assert list(dataframe.columns) == ["MD", "C1", "C2"]


def test_project_excel_dataset_manager_flags_missing_depth_column(tmp_path):
    from projects import list_project_excel_datasets, save_project_excel_dataset

    save_project_excel_dataset(
        _excel_bytes(depth_column="Time"),
        root=tmp_path,
        project_id="demo",
        file_name="No Depth.xlsx",
        name="No depth workbook",
    )

    dataset = list_project_excel_datasets(tmp_path, "demo")[0]

    assert dataset.status == "warning"
    assert dataset.depth_curve == ""
    assert "Не найдена глубинная колонка DEPT/DEPTH/MD на активном листе Excel." in dataset.warnings


def test_project_dataset_table_accepts_las_csv_and_excel_records(tmp_path):
    from projects import list_project_csv_datasets, list_project_excel_datasets, save_project_csv_dataset, save_project_excel_dataset

    save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
        version_label="raw",
    )
    save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.csv",
        name="Well A gas",
        well_id="well-a",
    )
    save_project_excel_dataset(
        _excel_bytes(),
        root=tmp_path,
        project_id="demo",
        file_name="Well A.xlsx",
        name="Well A workbook",
        well_id="well-a",
    )

    table = build_project_dataset_table(
        (
            *list_project_las_datasets(tmp_path, "demo"),
            *list_project_csv_datasets(tmp_path, "demo"),
            *list_project_excel_datasets(tmp_path, "demo"),
        )
    )

    assert set(table["Тип"]) == {"LAS", "CSV", "Excel"}
    assert "Well A workbook" in set(table["Dataset"])
    assert "MD" in set(table["Глубина"])


def test_project_excel_dataset_duplicate_names_get_unique_ids(tmp_path):
    from projects import save_project_excel_dataset

    first = save_project_excel_dataset(_excel_bytes(), root=tmp_path, project_id="demo", file_name="gas.xlsx", name="Gas")
    second = save_project_excel_dataset(_excel_bytes(), root=tmp_path, project_id="demo", file_name="gas.xlsx", name="Gas")

    assert first.id != second.id
    assert second.id.endswith("-2")


def test_project_excel_dataset_rejects_empty_bytes(tmp_path):
    from projects import save_project_excel_dataset

    with pytest.raises(ValueError):
        save_project_excel_dataset(b"", root=tmp_path, project_id="demo")
