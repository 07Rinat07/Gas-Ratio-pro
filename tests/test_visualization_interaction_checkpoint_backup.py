from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from services.visualization_interaction_checkpoint import VisualizationInteractionCheckpointStore
from services.visualization_interaction_checkpoint_backup import (
    VisualizationInteractionCheckpointBackupService,
)
from services.visualization_interaction_checkpoint_repository import (
    VisualizationInteractionCheckpointRepository,
)
from services.visualization_interaction_events import VisualizationInteractionEvent
from services.visualization_interaction_journal import VisualizationInteractionJournal
from services.visualization_interaction_session import VisualizationInteractionSession
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_viewport_controller import ViewportCommand


def _store(checkpoint_id: str) -> VisualizationInteractionCheckpointStore:
    session = VisualizationInteractionSession(
        InteractiveViewport(1000.0, 1100.0, 0.0, 500.0, inverted=True, unit="M")
    )
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(
        session, VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0))
    )
    store = VisualizationInteractionCheckpointStore(capacity=4)
    store.create(session, journal, checkpoint_id=checkpoint_id)
    return store


def _repository(tmp_path: Path) -> VisualizationInteractionCheckpointRepository:
    repository = VisualizationInteractionCheckpointRepository(tmp_path / "source")
    base = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    repository.save(_store("one"), name="one", timestamp=base)
    repository.save(_store("two"), name="two", timestamp=base + timedelta(minutes=1))
    return repository


def test_backup_and_restore_repository(tmp_path: Path):
    service = VisualizationInteractionCheckpointBackupService()
    source = _repository(tmp_path)
    metadata = service.create_backup(source, tmp_path / "backup.zip")
    destination = VisualizationInteractionCheckpointRepository(tmp_path / "restored")

    result = service.restore_backup(metadata.path, destination)

    assert metadata.file_count == 2
    assert len(result.restored_files) == 2
    assert destination.load_latest()[0].latest.checkpoint_id == "two"


def test_backup_metadata_is_serializable(tmp_path: Path):
    metadata = VisualizationInteractionCheckpointBackupService().create_backup(
        _repository(tmp_path), tmp_path / "backup.zip"
    )
    payload = metadata.to_dict()
    assert payload["file_count"] == 2
    assert len(payload["checksum_sha256"]) == 64


def test_restore_skips_existing_files_by_default(tmp_path: Path):
    service = VisualizationInteractionCheckpointBackupService()
    source = _repository(tmp_path)
    archive = service.create_backup(source, tmp_path / "backup.zip")
    result = service.restore_backup(archive.path, source)
    assert result.restored_files == ()
    assert len(result.skipped_files) == 2


def test_restore_overwrites_existing_files_when_requested(tmp_path: Path):
    service = VisualizationInteractionCheckpointBackupService()
    source = _repository(tmp_path)
    archive = service.create_backup(source, tmp_path / "backup.zip")
    result = service.restore_backup(archive.path, source, overwrite=True)
    assert len(result.restored_files) == 2
    assert result.skipped_files == ()


def test_restore_rejects_tampered_checkpoint_content(tmp_path: Path):
    service = VisualizationInteractionCheckpointBackupService()
    source = _repository(tmp_path)
    archive_path = Path(service.create_backup(source, tmp_path / "backup.zip").path)
    with ZipFile(archive_path, "r") as original:
        manifest = original.read("manifest.json")
        names = [name for name in original.namelist() if name.startswith("checkpoints/")]
        contents = {name: original.read(name) for name in names}
    contents[names[0]] = b"tampered"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as rewritten:
        rewritten.writestr("manifest.json", manifest)
        for name, content in contents.items():
            rewritten.writestr(name, content)

    with pytest.raises(ValueError, match="mismatch"):
        service.restore_backup(archive_path, VisualizationInteractionCheckpointRepository(tmp_path / "x"))


def test_restore_rejects_unsafe_manifest_name(tmp_path: Path):
    archive = tmp_path / "unsafe.zip"
    manifest = {
        "schema": VisualizationInteractionCheckpointBackupService.SCHEMA,
        "version": "1.0",
        "created_at": "2026-07-10T00:00:00+00:00",
        "file_count": 1,
        "files": [{"name": "../escape.interaction-checkpoints.json", "size_bytes": 1, "checksum_sha256": "x", "format_version": "2.0"}],
    }
    with ZipFile(archive, "w") as output:
        output.writestr("manifest.json", json.dumps(manifest))
        output.writestr("checkpoints/../escape.interaction-checkpoints.json", b"x")

    with pytest.raises(ValueError, match="unsafe"):
        VisualizationInteractionCheckpointBackupService().restore_backup(
            archive, VisualizationInteractionCheckpointRepository(tmp_path / "target")
        )


def test_restore_rejects_invalid_zip(tmp_path: Path):
    path = tmp_path / "bad.zip"
    path.write_bytes(b"not zip")
    with pytest.raises(ValueError, match="valid ZIP"):
        VisualizationInteractionCheckpointBackupService().restore_backup(
            path, VisualizationInteractionCheckpointRepository(tmp_path / "target")
        )


def test_create_backup_rejects_directory_target(tmp_path: Path):
    target = tmp_path / "directory"
    target.mkdir()
    with pytest.raises(ValueError, match="directory"):
        VisualizationInteractionCheckpointBackupService().create_backup(
            _repository(tmp_path), target
        )
