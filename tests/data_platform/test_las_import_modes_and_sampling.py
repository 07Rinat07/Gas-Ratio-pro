from pathlib import Path

import pytest

from core.data_platform import LasHeaderMetadataScanner, validate_las_metadata
from services.data_platform_application_service import DataPlatformApplicationService, LasImportValidationError


def _write_las(path: Path, *, version: str = "1.2", rows: tuple[str, ...] = ("1000 10", "1001 11")) -> Path:
    path.write_text(
        "\n".join((
            "~V", f"VERS. {version}", "WRAP. NO",
            "~W", "WELL. Legacy-1", "STRT.M 1000", "STOP.M 1002", "STEP.M 1", "NULL. -999.25",
            "~C", "DEPT.M", "GR.API", "~A", *rows,
        )) + "\n",
        encoding="utf-8",
    )
    return path


def test_scanner_samples_multiple_rows_and_reports_stable_columns(tmp_path):
    result = LasHeaderMetadataScanner(max_sample_rows=4).scan(
        _write_las(tmp_path / "stable.las", version="2.0", rows=("1000 10", "1001 11", "1002 12"))
    )
    assert result.metadata["data_sample_row_count"] == 3
    assert result.metadata["data_column_counts"] == "2,2,2"
    assert result.metadata["data_column_count_stable"] is True
    assert "las.compatibility.inconsistent_data_columns" not in result.warnings


def test_scanner_reports_inconsistent_columns_and_validation_code(tmp_path):
    result = LasHeaderMetadataScanner(max_sample_rows=4).scan(
        _write_las(tmp_path / "unstable.las", version="2.0", rows=("1000 10", "1001 11 12", "1002 12"))
    )
    assert result.metadata["data_column_count_stable"] is False
    assert result.metadata["data_column_count_min"] == 2
    assert result.metadata["data_column_count_max"] == 3
    assert "las.compatibility.inconsistent_data_columns" in result.warnings
    assert "las.validation.inconsistent_data_columns" in {item.code for item in validate_las_metadata(result)}


def test_tolerant_mode_accepts_legacy_las_but_strict_mode_blocks_before_persistence(tmp_path):
    source = _write_las(tmp_path / "legacy.las")
    service = DataPlatformApplicationService(tmp_path / "projects")

    tolerant = service.register_source_file_result(project_id="project-a", source=source, import_mode="tolerant")
    assert tolerant.manifest.metadata["import_mode"] == "tolerant"
    assert tolerant.manifest.version == 1

    second_source = _write_las(tmp_path / "legacy-strict.las")
    with pytest.raises(LasImportValidationError) as exc_info:
        service.register_source_file_result(project_id="project-b", source=second_source, import_mode="strict")
    assert "las.validation.legacy_format" in {item.code for item in exc_info.value.findings}
    assert service.manifests.list("project-b") == ()


def test_lineage_projection_is_lightweight_and_chronological(tmp_path):
    service = DataPlatformApplicationService(tmp_path / "projects")
    first = service.register_source_file_result(
        project_id="project-a", source=_write_las(tmp_path / "v1.las", version="2.0"), import_mode="tolerant"
    )
    second = service.register_source_file_result(
        project_id="project-a", source=_write_las(tmp_path / "v2.las", version="2.0", rows=("1000 20", "1001 21")),
        previous_dataset_id=first.manifest.dataset_id,
        import_mode="strict",
    )
    rows = service.list_dataset_lineage("project-a", first.manifest.lineage_id)
    assert [row["version"] for row in rows] == [1, 2]
    assert rows[-1]["dataset_id"] == second.manifest.dataset_id
    assert "artifact_path" not in rows[-1]
    summaries = service.list_project_lineages("project-a")
    assert summaries[0]["version_count"] == 2
    assert summaries[0]["latest_version"] == 2
