from __future__ import annotations

import json
from pathlib import Path

import pytest

from projects.interpretation_intervals import create_interpretation_interval, load_interpretation_intervals
from projects.interpretation_revisions import InterpretationRevisionRepository


def _repo(tmp_path: Path) -> InterpretationRevisionRepository:
    return InterpretationRevisionRepository(
        root=tmp_path,
        project_id="project-a",
        well_id="well-a",
        interpretation_id="default",
    )


def _create_interval(tmp_path: Path, label: str, top: float, base: float):
    return create_interpretation_interval(
        root=tmp_path,
        project_id="project-a",
        well_id="well-a",
        interpretation_id="default",
        label=label,
        top=top,
        base=base,
    )


def test_create_list_compare_restore_and_delete_revision(tmp_path: Path) -> None:
    first = _create_interval(tmp_path, "A", 100, 110)
    repo = _repo(tmp_path)
    revision = repo.create(name="Baseline", note="Before edits")
    assert revision.interval_count == 1
    assert repo.list()[0].id == revision.id

    second = _create_interval(tmp_path, "B", 120, 130)
    diff = repo.compare(revision.id)
    assert [item.id for item in diff.added] == [second.id]
    assert not diff.removed
    assert diff.unchanged_count == 1

    restored = repo.restore(revision.id, expected_current_state_token=diff.current_state_token)
    assert restored.id == revision.id
    assert [item.id for item in load_interpretation_intervals(tmp_path, "project-a", "well-a").intervals] == [first.id]
    assert repo.delete(revision.id) is True
    assert repo.list() == ()


def test_restore_rejects_stale_preview(tmp_path: Path) -> None:
    _create_interval(tmp_path, "A", 100, 110)
    repo = _repo(tmp_path)
    revision = repo.create(name="Baseline")
    preview = repo.compare(revision.id)
    _create_interval(tmp_path, "B", 120, 130)
    with pytest.raises(ValueError, match="изменилось"):
        repo.restore(revision.id, expected_current_state_token=preview.current_state_token)


def test_snapshot_includes_workspace_json_and_excludes_revision_store(tmp_path: Path) -> None:
    _create_interval(tmp_path, "A", 100, 110)
    repo = _repo(tmp_path)
    settings_path = repo.workspace_dir / "display_settings.json"
    settings_path.write_text(json.dumps({"visible": False}), encoding="utf-8")
    first = repo.create(name="One")
    second = repo.create(name="Two")
    payload = json.loads((repo.revision_dir / f"{second.id}.json").read_text(encoding="utf-8"))
    assert "display_settings.json" in payload["files"]
    assert all(not name.startswith(".revisions/") for name in payload["files"])
    assert first.id != second.id


def test_prune_keeps_latest_revisions(tmp_path: Path) -> None:
    _create_interval(tmp_path, "A", 100, 110)
    repo = _repo(tmp_path)
    revisions = [repo.create(name=f"R{index}") for index in range(4)]
    removed = repo.prune(keep_latest=2)
    assert len(removed) == 2
    assert len(repo.list()) == 2
    assert set(removed).issubset({item.id for item in revisions})


def test_catalog_duplicate_does_not_copy_revision_history(tmp_path: Path) -> None:
    from projects.interpretation_catalog import InterpretationCatalogRepository

    catalog = InterpretationCatalogRepository(root=tmp_path, project_id="project-a", well_id="well-a")
    catalog.list()
    _create_interval(tmp_path, "A", 100, 110)
    revisions = _repo(tmp_path)
    revisions.create(name="Baseline")

    duplicate = catalog.duplicate("default", name="Copy", target_id="copy")
    duplicate_revisions = InterpretationRevisionRepository(
        root=tmp_path,
        project_id="project-a",
        well_id="well-a",
        interpretation_id=duplicate.id,
    )
    assert duplicate_revisions.list() == ()
