from pathlib import Path
import json
import zipfile
import io

import pytest

from projects import create_project
from projects.data_exchange import (
    build_data_exchange_record_table,
    build_exchange_issue_table,
    build_project_exchange_manifest,
    build_project_exchange_zip,
    build_xlsx_bytes,
    delete_data_exchange_record,
    export_rows_csv,
    export_rows_geojson,
    export_rows_json,
    import_csv_text,
    import_json_text,
    list_data_exchange_records,
    normalize_exchange_profile,
    read_xlsx_bytes,
    save_data_exchange_record,
    summarize_data_exchange,
    validate_exchange_table,
)


def test_data_exchange_record_crud_summary_and_table(tmp_path: Path):
    project = create_project(tmp_path, name="Exchange Demo")

    saved = save_data_exchange_record(
        tmp_path,
        project.id,
        {
            "id": "csv-import-1",
            "name": "Well tops CSV import",
            "direction": "import",
            "format": "csv",
            "source_path": "incoming/tops.csv",
            "status": "done",
            "rows": 2,
            "columns": 3,
            "warnings": ["No TVD column"],
        },
    )
    records = list_data_exchange_records(tmp_path, project.id)
    table = build_data_exchange_record_table(records)
    summary = summarize_data_exchange(records)

    assert records == (saved,)
    assert table[0]["Формат"] == "CSV"
    assert table[0]["Предупреждения"] == 1
    assert summary.imports == 1
    assert summary.rows == 2

    assert delete_data_exchange_record(tmp_path, project.id, "csv-import-1") is True
    assert list_data_exchange_records(tmp_path, project.id) == ()


def test_csv_json_geojson_roundtrip_and_validation():
    rows = [
        {"well": "A-1", "md": 1000, "lat": 51.1, "lon": 71.4},
        {"well": "A-2", "md": 1100, "lat": 51.2, "lon": 71.5},
    ]

    csv_text = export_rows_csv(rows)
    parsed_csv = import_csv_text(csv_text, required_columns=["well", "md"])
    json_text = export_rows_json(rows)
    parsed_json = import_json_text(json_text, required_columns=["well"])
    geojson = json.loads(export_rows_geojson(rows))

    assert parsed_csv[0]["well"] == "A-1"
    assert parsed_json[1]["md"] == 1100
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2

    issues = validate_exchange_table([{"well": "A-1"}], required_columns=["md"])
    issue_table = build_exchange_issue_table(issues)
    assert issues[0].severity == "error"
    assert issue_table[0]["Код"] == "missing-column"

    with pytest.raises(ValueError, match="Отсутствует"):
        import_csv_text("well\nA-1\n", required_columns=["md"])


def test_xlsx_bytes_roundtrip():
    data = build_xlsx_bytes([{"well": "A-1", "md": 1000}, {"well": "A-2", "md": 1100}])
    rows = read_xlsx_bytes(data)

    assert rows[0]["well"] == "A-1"
    assert rows[1]["md"] == 1100


def test_exchange_profile_normalization_and_invalid_format():
    profile = normalize_exchange_profile(
        {
            "name": "CSV tops profile",
            "format": "csv",
            "direction": "import",
            "delimiter": ";",
            "required_columns": ["well", "top", "md"],
            "column_mapping": {"WELL_NAME": "well"},
        }
    )

    assert profile.id == "csv-tops-profile"
    assert profile.delimiter == ";"
    assert profile.column_mapping["WELL_NAME"] == "well"

    with pytest.raises(ValueError, match="Формат"):
        normalize_exchange_profile({"name": "bad", "format": "parquet"})


def test_project_exchange_manifest_and_zip(tmp_path: Path):
    project = create_project(tmp_path, name="Exchange ZIP Demo")
    project_dir = tmp_path / project.id
    (project_dir / "subdir").mkdir()
    (project_dir / "subdir" / "data.json").write_text('{"ok": true}', encoding="utf-8")

    manifest = build_project_exchange_manifest(tmp_path, project.id)
    zip_bytes = build_project_exchange_zip(tmp_path, project.id, include_patterns=["subdir/*.json"])

    assert manifest["schema"] == "gas-ratio-pro.project-exchange.v1"
    assert any(item["path"] == "subdir/data.json" for item in manifest["files"])

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert "manifest.json" in archive.namelist()
        assert "subdir/data.json" in archive.namelist()
