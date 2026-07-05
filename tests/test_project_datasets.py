from __future__ import annotations

import pandas as pd

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
