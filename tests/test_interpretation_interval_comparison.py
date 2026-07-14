from dataclasses import replace

import pytest

from projects.interpretation_interval_comparison import (
    InterpretationIntervalTransferService,
    compare_interpretation_intervals,
)
from projects.interpretation_intervals import (
    InterpretationIntervalSet,
    build_interpretation_interval,
    load_interpretation_intervals,
    save_interpretation_intervals,
)


def _save(root, interpretation_id, intervals):
    save_interpretation_intervals(
        InterpretationIntervalSet(
            schema="",
            project_id="project",
            well_id="well",
            interpretation_id=interpretation_id,
            intervals=tuple(intervals),
        ),
        root,
    )


def test_compare_detects_added_removed_modified_and_unchanged(tmp_path):
    unchanged = build_interpretation_interval(label="A", top=100, base=110)
    modified_source = build_interpretation_interval(label="B", top=120, base=130)
    modified_target = replace(modified_source, label="B2", color="#FF0000")
    added = build_interpretation_interval(label="C", top=140, base=150)
    removed = build_interpretation_interval(label="D", top=160, base=170)
    _save(tmp_path, "source", (unchanged, modified_source, added))
    _save(tmp_path, "target", (unchanged, modified_target, removed))

    result = compare_interpretation_intervals(
        root=tmp_path,
        project_id="project",
        well_id="well",
        source_interpretation_id="source",
        target_interpretation_id="target",
    )

    assert result.added_count == 1
    assert result.removed_count == 1
    assert result.modified_count == 1
    assert result.unchanged_count == 1
    modified = next(item for item in result.differences if item.status == "modified")
    assert modified.changed_fields == ("label", "color")


def test_transfer_overwrite_is_one_undoable_operation(tmp_path):
    shared = build_interpretation_interval(label="Source", top=100, base=110)
    target_shared = replace(shared, label="Target")
    added = build_interpretation_interval(label="Added", top=120, base=130)
    _save(tmp_path, "source", (shared, added))
    _save(tmp_path, "target", (target_shared,))
    state = {}
    service = InterpretationIntervalTransferService(
        state,
        root=tmp_path,
        project_id="project",
        well_id="well",
        source_interpretation_id="source",
        target_interpretation_id="target",
    )
    preview = service.preview((shared.id, added.id), conflict_policy="overwrite")
    result = service.apply(preview, expected_confirmation_token=preview.confirmation_token)

    assert result.added_count == 1
    assert result.overwritten_count == 1
    saved = load_interpretation_intervals(tmp_path, "project", "well", "target")
    assert {item.label for item in saved.intervals} == {"Source", "Added"}

    from projects.interpretation_interval_manager import InterpretationIntervalManager
    manager = InterpretationIntervalManager(
        state,
        root=tmp_path,
        project_id="project",
        well_id="well",
        interpretation_id="target",
    )
    assert manager.undo() is True
    restored = load_interpretation_intervals(tmp_path, "project", "well", "target")
    assert [item.label for item in restored.intervals] == ["Target"]


def test_transfer_rejects_stale_preview(tmp_path):
    source = build_interpretation_interval(label="Source", top=100, base=110)
    _save(tmp_path, "source", (source,))
    _save(tmp_path, "target", ())
    service = InterpretationIntervalTransferService(
        {}, root=tmp_path, project_id="project", well_id="well",
        source_interpretation_id="source", target_interpretation_id="target",
    )
    preview = service.preview((source.id,))
    _save(tmp_path, "target", (build_interpretation_interval(label="External", top=200, base=210),))
    with pytest.raises(ValueError, match="изменились"):
        service.apply(preview, expected_confirmation_token=preview.confirmation_token)


def test_transfer_can_skip_or_copy_uuid_conflicts(tmp_path):
    source = build_interpretation_interval(label="Source", top=100, base=110)
    target = replace(source, label="Target")
    _save(tmp_path, "source", (source,))
    _save(tmp_path, "target", (target,))
    state = {}
    service = InterpretationIntervalTransferService(
        state, root=tmp_path, project_id="project", well_id="well",
        source_interpretation_id="source", target_interpretation_id="target",
    )
    skip = service.preview((source.id,), conflict_policy="skip")
    skipped = service.apply(skip, expected_confirmation_token=skip.confirmation_token)
    assert skipped.skipped_count == 1
    copy = service.preview((source.id,), conflict_policy="copy")
    copied = service.apply(copy, expected_confirmation_token=copy.confirmation_token)
    assert copied.copied_count == 1
    saved = load_interpretation_intervals(tmp_path, "project", "well", "target")
    assert len(saved.intervals) == 2
    assert len({item.id for item in saved.intervals}) == 2
