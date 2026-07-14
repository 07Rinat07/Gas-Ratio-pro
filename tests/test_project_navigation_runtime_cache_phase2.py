from __future__ import annotations

import json
from pathlib import Path

from core.project_navigation_runtime_cache import ProjectNavigationRuntimeCache


def _write_metadata(root: Path, project_id: str, name: str, payload: object) -> None:
    path = root / project_id / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_navigation_cache_hits_until_metadata_changes(tmp_path: Path) -> None:
    _write_metadata(tmp_path, "p1", "project.json", {"name": "A"})
    cache = ProjectNavigationRuntimeCache(max_projects=2)

    cold = cache.lookup(tmp_path, "p1")
    assert not cold.hit
    assert cold.reason == "cold"

    cache.store(
        project_id="p1", token=cold.token,
        tree=({"id": "project:p1", "title": "A"},),
        counts={"calculations": 0}, metadata_files=cold.metadata_files,
    )
    hit = cache.lookup(tmp_path, "p1")
    assert hit.hit
    assert hit.tree[0]["id"] == "project:p1"

    _write_metadata(tmp_path, "p1", "well.json", {"name": "W1"})
    changed = cache.lookup(tmp_path, "p1")
    assert not changed.hit
    assert changed.reason == "metadata-changed"
    assert cache.snapshot()["invalidations"] == 1


def test_navigation_cache_is_bounded_and_snapshot_is_serializable(tmp_path: Path) -> None:
    cache = ProjectNavigationRuntimeCache(max_projects=2)
    for project_id in ("p1", "p2", "p3"):
        _write_metadata(tmp_path, project_id, "project.json", {"id": project_id})
        lookup = cache.lookup(tmp_path, project_id)
        cache.store(
            project_id=project_id, token=lookup.token,
            tree=({"id": project_id},), counts={}, metadata_files=lookup.metadata_files,
        )

    snapshot = cache.snapshot()
    assert snapshot["entries"] == 2
    assert snapshot["evictions"] == 1
    assert snapshot["projects"] == ["p2", "p3"]
    json.dumps(snapshot)
