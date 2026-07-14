from pathlib import Path

import pytest

from projects.interpretation_interval_manager import (
    InterpretationIntervalManager,
    InterpretationIntervalOverlapError,
)


def _manager(tmp_path: Path, state: dict) -> InterpretationIntervalManager:
    return InterpretationIntervalManager(
        state,
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        interpretation_id="primary",
    )


def test_manager_lists_and_finds_intervals_by_uuid(tmp_path: Path):
    manager = _manager(tmp_path, {})
    second = manager.create(label="B", top=120.0, base=130.0)
    first = manager.create(label="A", top=100.0, base=110.0)

    assert manager.list_intervals() == (first, second)
    assert manager.get_interval(second.id) == second
    with pytest.raises(KeyError, match="Интервал не найден"):
        manager.get_interval("missing")


def test_overlap_analysis_ignores_touching_boundaries(tmp_path: Path):
    manager = _manager(tmp_path, {})
    created = manager.create(label="A", top=100.0, base=110.0)

    assert manager.find_overlaps(top=110.0, base=120.0) == ()
    overlaps = manager.find_overlaps(top=105.0, base=115.0)
    assert len(overlaps) == 1
    assert overlaps[0].interval_id == created.id
    assert overlaps[0].overlap_top == 105.0
    assert overlaps[0].overlap_base == 110.0
    assert overlaps[0].overlap_thickness == 5.0


def test_optional_overlap_policy_preserves_backward_compatibility(tmp_path: Path):
    manager = _manager(tmp_path, {})
    manager.create(label="A", top=100.0, base=110.0)

    allowed = manager.create(label="B", top=105.0, base=115.0)
    assert manager.get_interval(allowed.id) == allowed

    with pytest.raises(InterpretationIntervalOverlapError, match="пересекается"):
        manager.create(label="C", top=108.0, base=120.0, reject_overlaps=True)


def test_update_excludes_current_interval_from_overlap_check(tmp_path: Path):
    manager = _manager(tmp_path, {})
    first = manager.create(label="A", top=100.0, base=110.0)
    manager.create(label="B", top=120.0, base=130.0)

    updated = manager.update(
        first.id,
        label="A edited",
        top=101.0,
        base=111.0,
        reject_overlaps=True,
    )
    assert updated.label == "A edited"

    with pytest.raises(InterpretationIntervalOverlapError):
        manager.update(
            first.id,
            label="A invalid",
            top=125.0,
            base=135.0,
            reject_overlaps=True,
        )


def test_manager_crud_remains_undo_redo_aware(tmp_path: Path):
    manager = _manager(tmp_path, {})
    created = manager.create(label="A", top=10.0, base=20.0)
    manager.delete(created.id)

    assert manager.list_intervals() == ()
    assert manager.undo() is True
    assert manager.get_interval(created.id).label == "A"
    assert manager.redo() is True
    assert manager.list_intervals() == ()
