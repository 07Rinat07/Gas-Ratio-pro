from pathlib import Path

import pytest

from core.data_platform import DatasetManifest, DatasetManifestRepository, DatasetProvenance
from services.data_platform_application_service import DataPlatformApplicationService


LAS = b"~Version\nVERS. 2.0\n~Well\nWELL. A-1\n~Curve\nDEPT.M : Depth\n~ASCII\n1000\n"


def test_registration_reports_existing_checksum_duplicate(tmp_path: Path) -> None:
    source = tmp_path / "a.las"
    source.write_bytes(LAS)
    service = DataPlatformApplicationService(tmp_path / "projects")

    first = service.register_source_file_result(project_id="p1", source=source)
    second = service.register_source_file_result(project_id="p1", source=source)

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert second.duplicate_dataset_ids == (first.manifest.dataset_id,)
    assert second.manifest.dataset_id != first.manifest.dataset_id
    assert second.manifest.artifact_path == first.manifest.artifact_path


def test_new_dataset_version_forms_immutable_lineage(tmp_path: Path) -> None:
    source1 = tmp_path / "well.las"
    source1.write_bytes(LAS)
    source2 = tmp_path / "well.las.v2.las"
    source2.write_bytes(LAS.replace(b"1000", b"1001"))
    service = DataPlatformApplicationService(tmp_path / "projects")

    v1 = service.register_source_file(project_id="p1", source=source1)
    v2 = service.register_source_file(project_id="p1", source=source2, previous_dataset_id=v1.dataset_id)

    assert v1.version == 1
    assert v2.version == 2
    assert v2.lineage_id == v1.lineage_id
    assert v2.previous_dataset_id == v1.dataset_id
    assert v2.provenance.source_dataset_ids == (v1.dataset_id,)
    assert service.manifests.list_lineage("p1", v1.lineage_id) == (v1, v2)
    assert v1.artifact_path != v2.artifact_path


def test_manifest_repository_rejects_mutating_existing_manifest(tmp_path: Path) -> None:
    repository = DatasetManifestRepository(tmp_path)
    original = DatasetManifest.create(
        project_id="p1", format_id="las", artifact_path="source/a.las",
        checksum_sha256="a" * 64, size_bytes=1,
    )
    repository.save(original)
    changed = DatasetManifest(
        **{**original.to_dict(), "size_bytes": 2, "provenance": DatasetProvenance(operation="import")}
    )
    with pytest.raises(FileExistsError):
        repository.save(changed)


def test_repository_rejects_skipped_lineage_version(tmp_path: Path) -> None:
    repository = DatasetManifestRepository(tmp_path)
    v1 = DatasetManifest.create(
        project_id="p1", format_id="las", artifact_path="source/a.las",
        checksum_sha256="a" * 64, size_bytes=1,
    )
    repository.save(v1)
    invalid = DatasetManifest.create(
        project_id="p1", format_id="las", artifact_path="source/b.las",
        checksum_sha256="b" * 64, size_bytes=2, version=3,
        lineage_id=v1.lineage_id, previous_dataset_id=v1.dataset_id,
    )
    with pytest.raises(ValueError, match="increment"):
        repository.save(invalid)
