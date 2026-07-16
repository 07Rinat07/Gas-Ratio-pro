import json

import pytest

from core.data_platform.dataset_manifest import DatasetManifest, DatasetProvenance

DIGEST = "a" * 64


def test_manifest_round_trip_preserves_provenance_and_metadata():
    manifest = DatasetManifest.create(
        project_id="project-a",
        well_id="well-1",
        format_id="LAS",
        artifact_path="source/well.las",
        checksum_sha256=DIGEST,
        size_bytes=123,
        source_name="well.las",
        unit_system="metric",
        metadata={"curve_count": 4, "indexed": True},
        provenance=DatasetProvenance(operation="import", actor="engineer", application_version="v1"),
    )
    restored = DatasetManifest.from_dict(manifest.to_dict())
    assert restored == manifest
    json.dumps(manifest.to_dict(), ensure_ascii=False)


def test_manifest_rejects_escaping_artifact_path():
    with pytest.raises(ValueError, match="artifact_path"):
        DatasetManifest.create(
            project_id="project-a",
            format_id="las",
            artifact_path="../outside.las",
            checksum_sha256=DIGEST,
            size_bytes=1,
        )


def test_manifest_rejects_invalid_checksum():
    with pytest.raises(ValueError, match="checksum"):
        DatasetManifest.create(
            project_id="project-a",
            format_id="las",
            artifact_path="source/a.las",
            checksum_sha256="invalid",
            size_bytes=1,
        )
