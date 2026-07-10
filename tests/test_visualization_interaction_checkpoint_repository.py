from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.visualization_interaction_checkpoint import VisualizationInteractionCheckpointStore
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
        session,
        VisualizationInteractionEvent.viewport(ViewportCommand.zoom(2.0)),
    )
    store = VisualizationInteractionCheckpointStore(capacity=4)
    store.create(session, journal, checkpoint_id=checkpoint_id)
    return store


def test_repository_saves_and_lists_compatible_files(tmp_path: Path):
    repository = VisualizationInteractionCheckpointRepository(tmp_path / "checkpoints")
    metadata = repository.save(
        _store("first"),
        name="Main Session",
        timestamp=datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc),
    )

    entries = repository.list_entries()

    assert len(entries) == 1
    assert entries[0].checkpoint_count == 1
    assert entries[0].format_version == "2.0"
    assert entries[0].name.endswith("-Main-Session.interaction-checkpoints.json")
    assert metadata.path == entries[0].path


def test_repository_loads_latest_compatible_file(tmp_path: Path):
    repository = VisualizationInteractionCheckpointRepository(tmp_path)
    base = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    repository.save(_store("old"), name="old", timestamp=base)
    repository.save(_store("new"), name="new", timestamp=base + timedelta(minutes=1))

    restored, _ = repository.load_latest()

    assert restored.latest is not None
    assert restored.latest.checkpoint_id == "new"


def test_repository_ignores_corrupted_and_unrelated_files(tmp_path: Path):
    repository = VisualizationInteractionCheckpointRepository(tmp_path)
    repository.save(_store("valid"), name="valid")
    (tmp_path / "broken.interaction-checkpoints.json").write_text("not-json", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    entries = repository.list_entries()
    restored, _ = repository.load_latest()

    assert len(entries) == 1
    assert restored.latest is not None
    assert restored.latest.checkpoint_id == "valid"


def test_repository_prunes_oldest_compatible_files(tmp_path: Path):
    repository = VisualizationInteractionCheckpointRepository(tmp_path)
    base = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    for index in range(4):
        repository.save(
            _store(str(index)),
            name=str(index),
            timestamp=base + timedelta(minutes=index),
        )

    removed = repository.prune(keep=2)
    entries = repository.list_entries()

    assert len(removed) == 2
    assert len(entries) == 2
    assert entries[0].name.startswith("20260710T100300")
    assert entries[1].name.startswith("20260710T100200")


def test_repository_keep_zero_removes_all_compatible_files(tmp_path: Path):
    repository = VisualizationInteractionCheckpointRepository(tmp_path)
    repository.save(_store("one"))

    removed = repository.prune(keep=0)

    assert len(removed) == 1
    assert repository.list_entries() == ()


def test_repository_rejects_negative_keep_count(tmp_path: Path):
    repository = VisualizationInteractionCheckpointRepository(tmp_path)

    with pytest.raises(ValueError, match="cannot be negative"):
        repository.prune(keep=-1)


def test_repository_reports_empty_restore(tmp_path: Path):
    repository = VisualizationInteractionCheckpointRepository(tmp_path)

    with pytest.raises(ValueError, match="no compatible"):
        repository.load_latest()


def test_repository_path_must_be_directory(tmp_path: Path):
    file_path = tmp_path / "file"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a directory"):
        VisualizationInteractionCheckpointRepository(file_path)
