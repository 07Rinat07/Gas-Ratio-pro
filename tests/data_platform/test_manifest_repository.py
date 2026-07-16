import json

from core.data_platform.dataset_manifest import DatasetManifest
from core.data_platform.manifest_repository import DatasetManifestRepository


def _manifest(project_id="project-a"):
    return DatasetManifest.create(
        project_id=project_id,
        format_id="las",
        artifact_path="source/a.las",
        checksum_sha256="1" * 64,
        size_bytes=10,
    )


def test_repository_saves_loads_and_summarizes_manifests(tmp_path):
    repository = DatasetManifestRepository(tmp_path)
    first = _manifest()
    second = DatasetManifest.create(
        project_id="project-a",
        format_id="segy",
        artifact_path="source/cube.sgy",
        checksum_sha256="2" * 64,
        size_bytes=90,
    )
    repository.save(first)
    repository.save(second)

    assert repository.load("project-a", first.dataset_id) == first
    snapshot = repository.snapshot("project-a")
    assert snapshot == {
        "project_id": "project-a",
        "dataset_count": 2,
        "total_size_bytes": 100,
        "formats": ["las", "segy"],
    }
    json.dumps(snapshot)


def test_repository_skips_corrupted_manifest_during_listing(tmp_path):
    repository = DatasetManifestRepository(tmp_path)
    valid = _manifest()
    directory = repository.save(valid).parent
    (directory / "broken.json").write_text("{broken", encoding="utf-8")
    assert repository.list("project-a") == (valid,)
