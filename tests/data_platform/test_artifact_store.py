import hashlib

import pytest

from core.data_platform.artifact_store import ArtifactStore


def test_store_file_copies_atomically_and_returns_relative_metadata(tmp_path):
    source = tmp_path / "source.las"
    source.write_bytes(b"~Version\nVERS. 2.0\n")
    store = ArtifactStore(tmp_path / "projects")

    location = store.store_file(project_id="project-a", source=source)

    assert location.relative_path == "source/source.las"
    assert location.size_bytes == source.stat().st_size
    assert location.checksum_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert store.resolve(project_id="project-a", relative_path=location.relative_path).read_bytes() == source.read_bytes()


def test_store_rejects_unsafe_project_and_filename(tmp_path):
    source = tmp_path / "a.las"
    source.write_text("x")
    store = ArtifactStore(tmp_path / "projects")
    with pytest.raises(ValueError):
        store.store_file(project_id="../outside", source=source)
    with pytest.raises(ValueError):
        store.store_file(project_id="project-a", source=source, filename="../a.las")


def test_resolve_rejects_path_escape(tmp_path):
    store = ArtifactStore(tmp_path / "projects")
    with pytest.raises(ValueError, match="escapes"):
        store.resolve(project_id="project-a", relative_path="../../secret")
