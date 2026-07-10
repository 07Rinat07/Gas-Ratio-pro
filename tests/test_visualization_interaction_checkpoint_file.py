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
