import json
import sqlite3
from pathlib import Path

from core.data_platform import LasHeaderMetadataScanner
from services.data_platform_application_service import DataPlatformApplicationService


def _legacy_las(path: Path) -> None:
    text = "~V\nVERS. 1.2\n~W\nWELL. Скважина-1\nSTRT.M 1000\nSTOP.M 1001\nSTEP.M 1\nNULL. -999.25\n~C\nDEPT.M\nGR.API\n~A\n1000;10\n"
    path.write_bytes(text.encode("cp1251"))


def test_scanner_reports_legacy_encoding_and_nonstandard_delimiter(tmp_path):
    source = tmp_path / "legacy.las"
    _legacy_las(source)
    result = LasHeaderMetadataScanner().scan(source)
    assert result.metadata["header_encoding"] == "cp1251"
    assert result.metadata["data_delimiter"] == "semicolon"
    assert "las.compatibility.legacy_encoding" in result.warnings
    assert "las.compatibility.nonstandard_data_delimiter" in result.warnings


def test_catalog_reconciliation_rebuilds_missing_projection(tmp_path):
    source = tmp_path / "legacy.las"
    _legacy_las(source)
    service = DataPlatformApplicationService(tmp_path / "projects")
    registered = service.register_source_file_result(project_id="p1", source=source)
    db = tmp_path / "projects" / "p1" / "datasets" / "catalog.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM datasets WHERE dataset_id = ?", (registered.manifest.dataset_id,))
        conn.commit()
    result = service.reconcile_catalog("p1")
    assert result["status"] == "rebuilt"
    assert result["missing_dataset_ids"] == [registered.manifest.dataset_id]
    assert service.catalog.snapshot("p1")["dataset_count"] == 1


def test_catalog_reconciliation_is_json_safe_when_consistent(tmp_path):
    source = tmp_path / "legacy.las"
    _legacy_las(source)
    service = DataPlatformApplicationService(tmp_path / "projects")
    service.register_source_file_result(project_id="p1", source=source)
    result = service.reconcile_catalog("p1")
    assert result["status"] == "consistent"
    json.dumps(result)
