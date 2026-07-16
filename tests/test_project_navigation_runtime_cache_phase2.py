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


def test_navigation_cache_preserves_multiple_profiles_for_one_project(tmp_path: Path) -> None:
    _write_metadata(tmp_path, "p1", "project.json", {"id": "p1"})
    cache = ProjectNavigationRuntimeCache(max_projects=2)

    root_lookup = cache.lookup(tmp_path, "p1", profile="root-only")
    cache.store(
        project_id="p1",
        profile="root-only",
        token=root_lookup.token,
        tree=({"id": "root"},),
        counts={"wells": 0},
        metadata_files=root_lookup.metadata_files,
    )

    wells_lookup = cache.lookup(tmp_path, "p1", profile="wells")
    assert wells_lookup.reason == "profile-cold"
    cache.store(
        project_id="p1",
        profile="wells",
        token=wells_lookup.token,
        tree=({"id": "well:w1"},),
        counts={"wells": 1},
        metadata_files=wells_lookup.metadata_files,
    )

    assert cache.lookup(tmp_path, "p1", profile="root-only").tree[0]["id"] == "root"
    assert cache.lookup(tmp_path, "p1", profile="wells").tree[0]["id"] == "well:w1"

    snapshot = cache.snapshot()
    assert snapshot["entries"] == 2
    assert snapshot["project_count"] == 1
    assert snapshot["project_profiles"] == {"p1": ["root-only", "wells"]}


def test_navigation_cache_project_eviction_removes_all_profiles(tmp_path: Path) -> None:
    cache = ProjectNavigationRuntimeCache(max_projects=1)
    for profile in ("root-only", "calculations"):
        _write_metadata(tmp_path, "p1", "project.json", {"id": "p1"})
        lookup = cache.lookup(tmp_path, "p1", profile=profile)
        cache.store(
            project_id="p1",
            profile=profile,
            token=lookup.token,
            tree=({"id": f"p1:{profile}"},),
            counts={},
            metadata_files=lookup.metadata_files,
        )

    _write_metadata(tmp_path, "p2", "project.json", {"id": "p2"})
    lookup = cache.lookup(tmp_path, "p2", profile="root-only")
    cache.store(
        project_id="p2",
        profile="root-only",
        token=lookup.token,
        tree=({"id": "p2"},),
        counts={},
        metadata_files=lookup.metadata_files,
    )

    snapshot = cache.snapshot()
    assert snapshot["projects"] == ["p2"]
    assert snapshot["entries"] == 1
    assert snapshot["evictions"] == 2
    assert not cache.lookup(tmp_path, "p1", profile="root-only").hit
