from pathlib import Path

import pytest

from projects.interpretation_interval_commands import (
    INTERVAL_HISTORY_SCHEMA,
    InterpretationIntervalCommandService,
    InterpretationIntervalHistoryConflict,
)
from projects.interpretation_intervals import (
    create_interpretation_interval,
    load_interpretation_intervals,
)


def _service(tmp_path: Path, state: dict, *, history_limit: int = 50):
    return InterpretationIntervalCommandService(
        state,
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        interpretation_id="primary",
        history_limit=history_limit,
    )


def test_create_update_delete_support_full_undo_redo_cycle(tmp_path: Path):
    state = {}
    service = _service(tmp_path, state)

    created = service.create(label="A", top=100.0, base=110.0)
    service.update(
        created.id,
        label="A edited",
        top=101.0,
        base=112.0,
        interval_type="gas",
        color="#112233",
        comment="edited",
    )
    assert service.delete(created.id) is True
    assert load_interpretation_intervals(tmp_path, "project-1", "well-1", "primary").intervals == ()

    assert service.undo() is True
    restored = load_interpretation_intervals(tmp_path, "project-1", "well-1", "primary").intervals[0]
    assert restored.label == "A edited"

    assert service.undo() is True
    original = load_interpretation_intervals(tmp_path, "project-1", "well-1", "primary").intervals[0]
    assert original.label == "A"

    assert service.undo() is True
    assert load_interpretation_intervals(tmp_path, "project-1", "well-1", "primary").intervals == ()
    assert service.undo() is False

    assert service.redo() is True
    assert service.redo() is True
    assert service.redo() is True
    assert load_interpretation_intervals(tmp_path, "project-1", "well-1", "primary").intervals == ()
    assert service.redo() is False


def test_new_command_clears_redo_stack(tmp_path: Path):
    state = {}
    service = _service(tmp_path, state)
    service.create(label="A", top=10.0, base=20.0)
    assert service.undo() is True
    assert service.can_redo is True

    service.create(label="B", top=30.0, base=40.0)
    assert service.can_redo is False
    assert service.history_status()["undo_count"] == 1


def test_history_is_bounded_and_json_compatible(tmp_path: Path):
    state = {}
    service = _service(tmp_path, state, history_limit=2)
    service.create(label="A", top=10.0, base=20.0)
    service.create(label="B", top=30.0, base=40.0)
    service.create(label="C", top=50.0, base=60.0)

    status = service.history_status()
    assert status["undo_count"] == 2
    history = next(value for key, value in state.items() if key.startswith("interpretation_interval_history::"))
    assert history["schema"] == INTERVAL_HISTORY_SCHEMA
    assert isinstance(history["undo"][0]["before"], list)
    assert isinstance(history["undo"][0]["after"][0], dict)


def test_external_repository_change_blocks_undo(tmp_path: Path):
    state = {}
    service = _service(tmp_path, state)
    service.create(label="A", top=10.0, base=20.0)

    create_interpretation_interval(
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        interpretation_id="primary",
        label="External",
        top=30.0,
        base=40.0,
    )

    with pytest.raises(InterpretationIntervalHistoryConflict, match="вне истории"):
        service.undo()


def test_loading_preserves_interval_timestamps(tmp_path: Path):
    state = {}
    service = _service(tmp_path, state)
    created = service.create(label="A", top=10.0, base=20.0)
    restored = load_interpretation_intervals(tmp_path, "project-1", "well-1", "primary").intervals[0]
    assert restored.created_at == created.created_at
    assert restored.updated_at == created.updated_at
