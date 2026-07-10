from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.visualization_interaction_checkpoint import VisualizationInteractionCheckpointStore
from services.visualization_interaction_checkpoint_file import (
    VisualizationInteractionCheckpointFileStore,
)
from services.visualization_interaction_events import VisualizationInteractionEvent
from services.visualization_interaction_journal import VisualizationInteractionJournal
from services.visualization_interaction_session import VisualizationInteractionSession
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_viewport_controller import ViewportCommand


def _store() -> VisualizationInteractionCheckpointStore:
    session = VisualizationInteractionSession(
        InteractiveViewport(1000.0, 1100.0, 0.0, 500.0, inverted=True, unit="M")
    )
    journal = VisualizationInteractionJournal()
    journal.dispatch_and_record(
        session,
        VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)),
    )
    result = VisualizationInteractionCheckpointStore(capacity=4)
    result.create(session, journal, checkpoint_id="zoomed")
    return result


def test_save_and_load_round_trip(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    source = _store()
    path = tmp_path / "nested" / "interaction-checkpoints.json"

    saved = repository.save(path, source)
    restored, loaded = repository.load(path)

    assert restored.to_dict() == source.to_dict()
    assert saved.checkpoint_count == 1
    assert loaded.checkpoint_count == 1
    assert saved.checksum_sha256 == loaded.checksum_sha256
    assert path.exists()


def test_saved_json_is_deterministic(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    store = _store()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    repository.save(first, store)
    repository.save(second, store)

    assert first.read_bytes() == second.read_bytes()


def test_save_replaces_existing_file_atomically(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    path = tmp_path / "state.json"
    path.write_text("old", encoding="utf-8")

    repository.save(path, _store())

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == repository.SCHEMA
    assert not list(tmp_path.glob(".state.json.*.tmp"))


def test_checksum_detects_tampering(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    path = tmp_path / "state.json"
    repository.save(path, _store())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["store"]["capacity"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="checksum mismatch"):
        repository.load(path)


def test_invalid_json_is_rejected(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_bytes(b"not-json")

    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        VisualizationInteractionCheckpointFileStore().load(path)


def test_unknown_schema_is_rejected(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    path = tmp_path / "state.json"
    repository.save(path, _store())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema"] = "unknown"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported.*schema"):
        repository.load(path)


def test_missing_file_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="does not exist"):
        VisualizationInteractionCheckpointFileStore().load(tmp_path / "missing.json")


def test_directory_path_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="directory"):
        VisualizationInteractionCheckpointFileStore().save(tmp_path, _store())


def test_current_format_contains_explicit_content_metadata(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    path = tmp_path / "state.json"
    metadata = repository.save(path, _store())
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["version"] == "2.0"
    assert payload["content_type"] == "visualization-interaction-checkpoints"
    assert payload["content_version"] == "1.0"
    assert metadata.format_version == "2.0"
    assert metadata.migrated_from_version == ""


def test_legacy_v1_file_is_loaded_and_reported_as_migrated(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    store = _store()
    raw_store = store.to_dict()
    legacy_payload = {
        "schema": repository.SCHEMA,
        "version": "1.0",
        "store": raw_store,
        "store_checksum_sha256": __import__("hashlib").sha256(
            repository._canonical_bytes(raw_store)
        ).hexdigest(),
    }
    path = tmp_path / "legacy.json"
    path.write_bytes(repository._canonical_bytes(legacy_payload))

    restored, metadata = repository.load(path)

    assert restored.to_dict() == store.to_dict()
    assert metadata.format_version == "2.0"
    assert metadata.migrated_from_version == "1.0"


def test_migrate_file_rewrites_legacy_file_to_current_version(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    store = _store()
    raw_store = store.to_dict()
    legacy_payload = {
        "schema": repository.SCHEMA,
        "version": "1.0",
        "store": raw_store,
        "store_checksum_sha256": __import__("hashlib").sha256(
            repository._canonical_bytes(raw_store)
        ).hexdigest(),
    }
    path = tmp_path / "legacy.json"
    path.write_bytes(repository._canonical_bytes(legacy_payload))

    metadata = repository.migrate_file(path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["version"] == "2.0"
    assert metadata.format_version == "2.0"
    assert metadata.migrated_from_version == ""


def test_unknown_future_version_is_rejected(tmp_path: Path):
    repository = VisualizationInteractionCheckpointFileStore()
    path = tmp_path / "future.json"
    repository.save(path, _store())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = "99.0"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported.*version"):
        repository.load(path)
