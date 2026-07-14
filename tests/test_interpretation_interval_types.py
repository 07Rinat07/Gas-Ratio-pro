from pathlib import Path

import pytest

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_interval_types import InterpretationIntervalTypeRepository


def test_repository_returns_defaults_without_creating_file(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")

    items = repository.list()

    assert {item.id for item in items} >= {"undefined", "reservoir", "pay", "gas", "oil", "water"}
    assert not (tmp_path / "project" / "interpretation_interval_types.json").exists()


def test_repository_upserts_and_persists_custom_type(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")

    created = repository.upsert(type_id="tight gas", name="Плотный газ", color="#123abc", description="Test")
    loaded = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project").get(created.id)

    assert created.id == "tight_gas"
    assert created.color == "#123ABC"
    assert loaded == created


def test_repository_updates_existing_type_without_changing_created_at(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    first = repository.upsert(type_id="custom", name="Первый", color="#112233")

    updated = repository.upsert(type_id="custom", name="Второй", color="#445566")

    assert updated.name == "Второй"
    assert updated.created_at == first.created_at


def test_repository_deletes_type_and_is_project_scoped(tmp_path: Path) -> None:
    first = InterpretationIntervalTypeRepository(root=tmp_path, project_id="first")
    second = InterpretationIntervalTypeRepository(root=tmp_path, project_id="second")
    first.upsert(type_id="custom", name="Custom", color="#112233")

    assert first.delete("custom") is True
    assert first.delete("custom") is False
    assert second.get("custom") is None


def test_repository_validates_color(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")

    with pytest.raises(ValueError, match="HEX"):
        repository.upsert(type_id="bad", name="Bad", color="red")

from projects.interpretation_intervals import create_interpretation_interval


def test_repository_reports_project_wide_type_usage(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="custom", name="Custom", color="#112233")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        interpretation_id="default",
        label="A",
        top=100,
        base=110,
        interval_type="custom",
    )
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-b",
        interpretation_id="secondary",
        label="B",
        top=200,
        base=210,
        interval_type="custom",
    )

    usage = repository.usage("custom")

    assert usage.interval_count == 2
    assert usage.well_count == 2
    assert usage.interpretation_count == 2
    assert usage.in_use is True


def test_repository_refuses_to_delete_type_used_by_intervals(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="custom", name="Custom", color="#112233")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        label="A",
        top=100,
        base=110,
        interval_type="custom",
    )

    with pytest.raises(ValueError, match="используется"):
        repository.delete("custom")

    assert repository.get("custom") is not None


def test_repository_reassigns_type_across_project_and_applies_target_color(tmp_path: Path) -> None:
    from projects.interpretation_intervals import load_interpretation_intervals

    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#AABBCC")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        interpretation_id="default",
        label="A",
        top=100,
        base=110,
        interval_type="source",
        color="#010203",
    )
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-b",
        interpretation_id="secondary",
        label="B",
        top=200,
        base=210,
        interval_type="source",
        color="#040506",
    )

    result = repository.reassign("source", "target", apply_target_color=True)

    assert result.interval_count == 2
    assert result.well_count == 2
    assert result.interpretation_count == 2
    for well_id, interpretation_id in (("well-a", "default"), ("well-b", "secondary")):
        interval = load_interpretation_intervals(
            tmp_path, "project", well_id, interpretation_id
        ).intervals[0]
        assert interval.interval_type == "target"
        assert interval.color == "#AABBCC"


def test_repository_reassign_and_delete_preserves_interval_color_when_requested(tmp_path: Path) -> None:
    from projects.interpretation_intervals import load_interpretation_intervals

    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#AABBCC")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        label="A",
        top=100,
        base=110,
        interval_type="source",
        color="#010203",
    )

    result = repository.reassign_and_delete(
        "source", "target", apply_target_color=False
    )

    interval = load_interpretation_intervals(
        tmp_path, "project", "well-a", "default"
    ).intervals[0]
    assert result.interval_count == 1
    assert interval.interval_type == "target"
    assert interval.color == "#010203"
    assert repository.get("source") is None


def test_repository_reassign_rejects_same_or_missing_target_type(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")

    with pytest.raises(ValueError, match="должны отличаться"):
        repository.reassign("source", "source")
    with pytest.raises(KeyError, match="missing"):
        repository.reassign("source", "missing")


def test_repository_previews_project_wide_reassignment_without_changing_data(tmp_path: Path) -> None:
    from projects.interpretation_intervals import load_interpretation_intervals

    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#AABBCC")
    first = create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-b",
        interpretation_id="secondary",
        label="B",
        top=200,
        base=212,
        interval_type="source",
        color="#010203",
    )
    second = create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        interpretation_id="default",
        label="A",
        top=100,
        base=110,
        interval_type="source",
        color="#040506",
    )

    preview = repository.preview_reassignment("source", "target", apply_target_color=True)

    assert preview.interval_count == 2
    assert preview.well_count == 2
    assert preview.interpretation_count == 2
    assert preview.target_color_applied is True
    assert [item.interval_id for item in preview.items] == [second.id, first.id]
    assert preview.items[0].thickness == 10.0
    assert load_interpretation_intervals(tmp_path, "project", "well-a", "default").intervals[0].interval_type == "source"
    assert load_interpretation_intervals(tmp_path, "project", "well-b", "secondary").intervals[0].interval_type == "source"


def test_repository_reassignment_preview_validates_types(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")

    with pytest.raises(ValueError, match="должны отличаться"):
        repository.preview_reassignment("source", "source")
    with pytest.raises(KeyError, match="missing"):
        repository.preview_reassignment("source", "missing")


def test_reassignment_rejects_stale_preview_after_interval_change(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#445566")
    manager = InterpretationIntervalManager(
        {}, root=tmp_path, project_id="project", well_id="well-a", interpretation_id="default"
    )
    interval = manager.create(label="A", top=100, base=110, interval_type="source", color="#010203")
    preview = repository.preview_reassignment("source", "target")

    manager.update(interval.id, label=interval.label, top=interval.top, base=interval.base, interval_type=interval.interval_type, color=interval.color, comment="changed after preview")

    with pytest.raises(ValueError, match="изменились после предварительного просмотра"):
        repository.reassign_and_delete(
            "source",
            "target",
            expected_confirmation_token=preview.confirmation_token,
        )

    current = manager.get_interval(interval.id)
    assert current.interval_type == "source"
    assert repository.get("source") is not None


def test_reassignment_accepts_current_preview_confirmation_token(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#445566")
    manager = InterpretationIntervalManager(
        {}, root=tmp_path, project_id="project", well_id="well-a", interpretation_id="default"
    )
    interval = manager.create(label="A", top=100, base=110, interval_type="source", color="#010203")
    preview = repository.preview_reassignment("source", "target")

    result = repository.reassign_and_delete(
        "source",
        "target",
        expected_confirmation_token=preview.confirmation_token,
    )

    assert result.interval_count == 1
    current = manager.get_interval(interval.id)
    assert current.interval_type == "target"
    assert repository.get("source") is None


def test_reassign_and_delete_appends_project_operation_journal(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#445566")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        interpretation_id="default",
        label="A",
        top=100,
        base=110,
        interval_type="source",
        color="#010203",
    )
    preview = repository.preview_reassignment("source", "target", apply_target_color=False)

    repository.reassign_and_delete(
        "source",
        "target",
        apply_target_color=False,
        expected_confirmation_token=preview.confirmation_token,
    )

    operations = repository.list_operations()
    assert len(operations) == 1
    operation = operations[0]
    assert operation.operation == "reassign_and_delete"
    assert operation.source_type_id == "source"
    assert operation.target_type_id == "target"
    assert operation.interval_count == 1
    assert operation.well_count == 1
    assert operation.interpretation_count == 1
    assert operation.target_color_applied is False
    assert operation.id
    assert operation.created_at.endswith("Z")
    assert (tmp_path / "project" / "interpretation_interval_type_operations.json").exists()


def test_failed_stale_reassignment_does_not_append_operation_journal(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#445566")
    manager = InterpretationIntervalManager(
        {}, root=tmp_path, project_id="project", well_id="well-a", interpretation_id="default"
    )
    interval = manager.create(label="A", top=100, base=110, interval_type="source")
    preview = repository.preview_reassignment("source", "target")
    manager.update(
        interval.id,
        label=interval.label,
        top=interval.top,
        base=interval.base,
        interval_type=interval.interval_type,
        color=interval.color,
        comment="changed",
    )

    with pytest.raises(ValueError, match="изменились после предварительного просмотра"):
        repository.reassign_and_delete(
            "source",
            "target",
            expected_confirmation_token=preview.confirmation_token,
        )

    assert repository.list_operations() == ()


def test_repository_undoes_last_reassign_and_delete(tmp_path: Path) -> None:
    from projects.interpretation_intervals import load_interpretation_intervals

    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    source = repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#445566")
    interval = create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        interpretation_id="default",
        label="A",
        top=100,
        base=110,
        interval_type="source",
        color="#010203",
    )
    preview = repository.preview_reassignment("source", "target", apply_target_color=True)
    repository.reassign_and_delete(
        "source",
        "target",
        apply_target_color=True,
        expected_confirmation_token=preview.confirmation_token,
    )

    operation = repository.undo_last_reassignment()

    restored = load_interpretation_intervals(
        tmp_path, "project", "well-a", "default"
    ).intervals[0]
    assert restored.id == interval.id
    assert restored.interval_type == "source"
    assert restored.color == "#010203"
    assert repository.get("source") == source
    assert operation.undone_at.endswith("Z")
    assert operation.undo_available is False
    assert repository.list_operations()[0].undone_at == operation.undone_at


def test_repository_blocks_undo_after_external_interval_change(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#445566")
    manager = InterpretationIntervalManager(
        {}, root=tmp_path, project_id="project", well_id="well-a", interpretation_id="default"
    )
    interval = manager.create(label="A", top=100, base=110, interval_type="source")
    preview = repository.preview_reassignment("source", "target")
    repository.reassign_and_delete(
        "source", "target", expected_confirmation_token=preview.confirmation_token
    )
    current = manager.get_interval(interval.id)
    manager.update(
        current.id,
        label=current.label,
        top=current.top,
        base=current.base,
        interval_type=current.interval_type,
        color=current.color,
        comment="changed after reassignment",
    )

    with pytest.raises(ValueError, match="Автоматическая отмена заблокирована"):
        repository.undo_last_reassignment()

    assert repository.get("source") is None
    assert repository.list_operations()[0].undo_available is True


def test_repository_only_undoes_latest_operation_once(tmp_path: Path) -> None:
    repository = InterpretationIntervalTypeRepository(root=tmp_path, project_id="project")
    repository.upsert(type_id="source", name="Source", color="#112233")
    repository.upsert(type_id="target", name="Target", color="#445566")
    create_interpretation_interval(
        root=tmp_path,
        project_id="project",
        well_id="well-a",
        label="A",
        top=100,
        base=110,
        interval_type="source",
    )
    preview = repository.preview_reassignment("source", "target")
    repository.reassign_and_delete(
        "source", "target", expected_confirmation_token=preview.confirmation_token
    )
    repository.undo_last_reassignment()

    with pytest.raises(ValueError, match="нельзя отменить"):
        repository.undo_last_reassignment()
