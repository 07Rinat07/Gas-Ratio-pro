from pathlib import Path

import pytest

from core.data_platform.las_metadata_scanner import LasHeaderMetadataScanner
from core.data_platform.las_validation import validate_las_metadata
from services.data_platform_application_service import DataPlatformApplicationService


def _las(rows: str, *, step: str = "0.5") -> bytes:
    return f"""~Version
VERS. 2.0
WRAP. NO
~Well
WELL. Demo
STRT.M 1000
STOP.M 1002
STEP.M {step}
NULL. -999.25
~Curve
DEPT.M
GR.API
~ASCII
{rows}
""".encode()


def test_scanner_reports_monotonic_depth_and_stable_step(tmp_path: Path) -> None:
    source = tmp_path / "stable.las"
    source.write_bytes(_las("1000.0 10\n1000.5 11\n1001.0 12\n1001.5 13\n"))
    result = LasHeaderMetadataScanner().scan(source)
    assert result.metadata["depth_monotonic"] is True
    assert result.metadata["depth_direction"] == "increasing"
    assert result.metadata["observed_step_stable"] is True
    assert result.metadata["declared_step_matches_observed"] is True


def test_scanner_reports_non_monotonic_and_unstable_step(tmp_path: Path) -> None:
    source = tmp_path / "unstable.las"
    source.write_bytes(_las("1000.0 10\n1000.5 11\n1000.25 12\n1001.5 13\n"))
    result = LasHeaderMetadataScanner().scan(source)
    assert result.metadata["depth_monotonic"] is False
    assert result.metadata["observed_step_stable"] is False
    findings = {item.code for item in validate_las_metadata(result)}
    assert "las.validation.non_monotonic_depth" in findings
    assert "las.validation.unstable_step" in findings


def test_compare_versions_and_lineage_properties(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    first_file = tmp_path / "first.las"
    second_file = tmp_path / "second.las"
    first_file.write_bytes(_las("1000.0 10\n1000.5 11\n"))
    second_file.write_bytes(_las("1000.0 10\n1000.5 12\n"))
    service = DataPlatformApplicationService(projects)
    first = service.register_source_file_result(project_id="project-a", source=first_file, actor="tester")
    second = service.register_source_file_result(
        project_id="project-a", source=second_file, actor="reviewer", previous_dataset_id=first.manifest.dataset_id
    )
    rows = service.list_dataset_lineage("project-a", first.manifest.lineage_id)
    assert rows[0]["checksum_sha256"] == first.manifest.checksum_sha256
    assert rows[1]["provenance_actor"] == "reviewer"
    comparison = service.compare_dataset_versions("project-a", first.manifest.dataset_id, second.manifest.dataset_id)
    assert comparison["checksum_changed"] is True
    assert comparison["left_version"] == 1
    assert comparison["right_version"] == 2


def test_compare_rejects_different_lineages(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    one = tmp_path / "one.las"
    two = tmp_path / "two.las"
    one.write_bytes(_las("1000 10\n1000.5 11\n"))
    two.write_bytes(_las("1000 20\n1000.5 21\n"))
    service = DataPlatformApplicationService(projects)
    left = service.register_source_file_result(project_id="project-a", source=one)
    right = service.register_source_file_result(project_id="project-a", source=two)
    with pytest.raises(ValueError, match="same lineage"):
        service.compare_dataset_versions("project-a", left.manifest.dataset_id, right.manifest.dataset_id)
