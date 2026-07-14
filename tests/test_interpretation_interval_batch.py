from pathlib import Path

import pytest

from projects.interpretation_interval_batch import InterpretationIntervalBatchService
from projects.interpretation_interval_manager import InterpretationIntervalManager


def _manager(tmp_path: Path, state: dict) -> InterpretationIntervalManager:
    return InterpretationIntervalManager(
        state,
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        interpretation_id="primary",
    )


def test_batch_assign_type_is_one_undoable_operation(tmp_path: Path):
    manager = _manager(tmp_path, {})
    first = manager.create(label="A", top=100, base=110, interval_type="old", color="#111111")
    second = manager.create(label="B", top=120, base=130, interval_type="old", color="#222222")
    manager.commands.clear_history()

    result = InterpretationIntervalBatchService(manager).assign_type(
        [first.id, second.id], interval_type="reservoir", color="#ABCDEF"
    )

    assert result.changed_count == 2
    assert {item.interval_type for item in manager.list_intervals()} == {"reservoir"}
    assert {item.color for item in manager.list_intervals()} == {"#ABCDEF"}
    assert manager.undo() is True
    restored = manager.list_intervals()
    assert [item.interval_type for item in restored] == ["old", "old"]
    assert [item.color for item in restored] == ["#111111", "#222222"]


def test_batch_assign_type_can_preserve_individual_colors(tmp_path: Path):
    manager = _manager(tmp_path, {})
    interval = manager.create(label="A", top=100, base=110, interval_type="old", color="#123456")

    InterpretationIntervalBatchService(manager).assign_type(
        [interval.id], interval_type="new", color=None
    )

    updated = manager.get_interval(interval.id)
    assert updated.interval_type == "new"
    assert updated.color == "#123456"


def test_batch_delete_is_one_undoable_operation(tmp_path: Path):
    manager = _manager(tmp_path, {})
    first = manager.create(label="A", top=100, base=110)
    second = manager.create(label="B", top=120, base=130)
    third = manager.create(label="C", top=140, base=150)
    manager.commands.clear_history()

    result = InterpretationIntervalBatchService(manager).delete([first.id, third.id])

    assert result.changed_count == 2
    assert manager.list_intervals() == (second,)
    assert manager.undo() is True
    assert {item.id for item in manager.list_intervals()} == {first.id, second.id, third.id}


def test_batch_operations_reject_empty_or_unknown_selection(tmp_path: Path):
    manager = _manager(tmp_path, {})
    service = InterpretationIntervalBatchService(manager)

    with pytest.raises(ValueError, match="хотя бы один"):
        service.delete([])
    with pytest.raises(KeyError, match="не найдены"):
        service.assign_type(["missing"], interval_type="new")


def test_batch_edit_metadata_replaces_source_and_appends_comment_as_one_operation(tmp_path: Path):
    manager = _manager(tmp_path, {})
    first = manager.create(label="A", top=100, base=110, comment="Первый", source="manual")
    second = manager.create(label="B", top=120, base=130, comment="", source="import")
    manager.commands.clear_history()

    result = InterpretationIntervalBatchService(manager).edit_metadata(
        [first.id, second.id],
        comment="Проверено геологом",
        comment_mode="append",
        source="reviewed",
    )

    assert result.changed_count == 2
    updated = {item.id: item for item in manager.list_intervals()}
    assert updated[first.id].comment == "Первый\nПроверено геологом"
    assert updated[second.id].comment == "Проверено геологом"
    assert {item.source for item in updated.values()} == {"reviewed"}
    assert manager.undo() is True
    restored = {item.id: item for item in manager.list_intervals()}
    assert restored[first.id].comment == "Первый"
    assert restored[second.id].comment == ""
    assert restored[first.id].source == "manual"
    assert restored[second.id].source == "import"


def test_batch_edit_metadata_supports_explicit_comment_clear(tmp_path: Path):
    manager = _manager(tmp_path, {})
    interval = manager.create(label="A", top=100, base=110, comment="Удалить", source="manual")

    result = InterpretationIntervalBatchService(manager).edit_metadata(
        [interval.id], comment="", comment_mode="replace"
    )

    assert result.changed_count == 1
    assert manager.get_interval(interval.id).comment == ""
    assert manager.get_interval(interval.id).source == "manual"


def test_batch_edit_metadata_validates_requested_changes(tmp_path: Path):
    manager = _manager(tmp_path, {})
    interval = manager.create(label="A", top=100, base=110)
    service = InterpretationIntervalBatchService(manager)

    with pytest.raises(ValueError, match="комментарий или источник"):
        service.edit_metadata([interval.id])
    with pytest.raises(ValueError, match="replace или append"):
        service.edit_metadata([interval.id], comment="x", comment_mode="merge")
    with pytest.raises(ValueError, match="длиннее 80"):
        service.edit_metadata([interval.id], source="x" * 81)
