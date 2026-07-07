from __future__ import annotations

from pathlib import Path

import pandas as pd

from las_editor.las_export_center import (
    LAS_EXPORT_CENTER_SCHEMA,
    LASExportCenter,
    ExportCenterRequest,
    build_export_center_preview,
    export_dataframe_from_center,
    normalize_export_format,
    normalize_export_path,
)
from las_editor.las_validator import LasValidationFinding


def _df() -> pd.DataFrame:
    return pd.DataFrame({"DEPT": [1000.0, 1000.5], "GR": [85.0, 90.0]})


def test_export_center_normalizes_format_and_path(tmp_path: Path):
    assert normalize_export_format(".LAS") == "las"
    assert normalize_export_path(tmp_path / "well_export", "csv").suffix == ".csv"


def test_export_center_preview_is_no_write_and_ui_ready(tmp_path: Path):
    target = tmp_path / "preview.las"
    result = build_export_center_preview(
        _df(),
        ExportCenterRequest(target_path=target, export_format="las"),
        las_text="~Version\nVERS. 2.0 : Version\n~ASCII\n1000 85\n",
    )

    assert result.schema == LAS_EXPORT_CENTER_SCHEMA
    assert result.status == "ready"
    assert result.is_ready
    assert not target.exists()
    assert "LAS Export Center" in result.markdown_report
    assert any(row["name"] == "target_path" for row in result.table_rows if "name" in row)


def test_export_center_blocks_source_overwrite(tmp_path: Path):
    source = tmp_path / "source.las"
    source.write_text("original", encoding="utf-8")

    result = export_dataframe_from_center(
        _df(),
        ExportCenterRequest(target_path=source, source_path=source, export_format="las", allow_overwrite=True),
        las_text="~Version\nVERS. 2.0 : Version\n",
    )

    assert result.status == "blocked"
    assert source.read_text(encoding="utf-8") == "original"
    assert any(issue.code == "SOURCE_OVERWRITE_BLOCKED" for issue in result.issues)


def test_export_center_writes_csv_with_safe_extension(tmp_path: Path):
    target = tmp_path / "table_export"
    result = LASExportCenter().export_dataframe(_df(), ExportCenterRequest(target_path=target, export_format="csv"))

    written = tmp_path / "table_export.csv"
    assert result.is_exported
    assert written.exists()
    assert "DEPT" in written.read_text(encoding="utf-8")


def test_export_center_blocks_validation_errors(tmp_path: Path):
    finding = LasValidationFinding("error", "TEST_ERROR", "Broken LAS")
    result = build_export_center_preview(
        _df(),
        ExportCenterRequest(target_path=tmp_path / "blocked.las"),
        las_text="~Version\n",
        validation_findings=[finding],
    )

    assert result.status == "blocked"
    assert any(issue.code == "TEST_ERROR" for issue in result.issues)
