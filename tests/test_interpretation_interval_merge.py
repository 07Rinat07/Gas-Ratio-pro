from pathlib import Path

import pytest

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_interval_merge import InterpretationIntervalMergeService
from projects.interpretation_intervals import build_interpretation_interval


def _manager(tmp_path: Path, state: dict, interpretation_id: str) -> InterpretationIntervalManager:
    return InterpretationIntervalManager(
        state,
        root=tmp_path,
        project_id="p1",
        well_id="w1",
        interpretation_id=interpretation_id,
    )


def _seed(tmp_path: Path, state: dict):
    base = _manager(tmp_path, state, "base")
    a = build_interpretation_interval(
        interval_id="11111111-1111-4111-8111-111111111111",
        label="A", top=100, base=110, interval_type="sand", color="#112233",
    )
    b = build_interpretation_interval(
        interval_id="22222222-2222-4222-8222-222222222222",
        label="B", top=120, base=130, interval_type="sand", color="#112233",
    )
    base.replace_all((a, b))
    _manager(tmp_path, state, "source").replace_all((a, b))
    _manager(tmp_path, state, "target").replace_all((a, b))
    return a, b


def test_three_way_merge_applies_non_conflicting_changes_as_one_undo(tmp_path: Path):
    state = {}
    a, b = _seed(tmp_path, state)
    source = _manager(tmp_path, state, "source")
    target = _manager(tmp_path, state, "target")
    source.update(a.id, label="A source", top=a.top, base=a.base, interval_type=a.interval_type,
                  color=a.color, comment=a.comment)
    target.update(b.id, label="B target", top=b.top, base=b.base, interval_type=b.interval_type,
                  color=b.color, comment=b.comment)

    service = InterpretationIntervalMergeService(
        state, root=tmp_path, project_id="p1", well_id="w1",
        base_interpretation_id="base", source_interpretation_id="source", target_interpretation_id="target",
    )
    preview = service.preview()
    assert preview.automatic_count == 1
    assert preview.conflict_count == 0
    result = service.apply(preview, expected_confirmation_token=preview.confirmation_token)
    assert result.automatic_count == 1
    assert {item.id: item.label for item in target.list_intervals()} == {a.id: "A source", b.id: "B target"}
    assert target.undo() is True
    assert {item.id: item.label for item in target.list_intervals()} == {a.id: "A", b.id: "B target"}


def test_three_way_merge_detects_and_resolves_conflict(tmp_path: Path):
    state = {}
    a, _ = _seed(tmp_path, state)
    for interpretation_id, label in (("source", "source edit"), ("target", "target edit")):
        manager = _manager(tmp_path, state, interpretation_id)
        manager.update(a.id, label=label, top=a.top, base=a.base, interval_type=a.interval_type,
                       color=a.color, comment=a.comment)
    service = InterpretationIntervalMergeService(
        state, root=tmp_path, project_id="p1", well_id="w1",
        base_interpretation_id="base", source_interpretation_id="source", target_interpretation_id="target",
    )
    preview = service.preview()
    assert preview.conflict_count == 1
    result = service.apply(
        preview,
        expected_confirmation_token=preview.confirmation_token,
        conflict_resolutions={a.id: "source"},
    )
    assert result.resolved_conflict_count == 1
    assert _manager(tmp_path, state, "target").get_interval(a.id).label == "source edit"


def test_three_way_merge_rejects_stale_preview(tmp_path: Path):
    state = {}
    a, _ = _seed(tmp_path, state)
    service = InterpretationIntervalMergeService(
        state, root=tmp_path, project_id="p1", well_id="w1",
        base_interpretation_id="base", source_interpretation_id="source", target_interpretation_id="target",
    )
    preview = service.preview()
    source = _manager(tmp_path, state, "source")
    source.update(a.id, label="changed", top=a.top, base=a.base, interval_type=a.interval_type,
                  color=a.color, comment=a.comment)
    with pytest.raises(ValueError, match="изменились после preview"):
        service.apply(preview, expected_confirmation_token=preview.confirmation_token)
