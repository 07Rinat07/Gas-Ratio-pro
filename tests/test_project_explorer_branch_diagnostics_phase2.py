from __future__ import annotations

from pathlib import Path

import projects.project_tree as project_tree_module
from core.project_navigation_runtime_cache import ProjectNavigationRuntimeCache
from projects import create_project


def test_project_tree_records_only_requested_branch_timings(tmp_path, monkeypatch) -> None:
    project = create_project(tmp_path, name="Diagnostics", project_id="diag")
    monkeypatch.setattr(project_tree_module, "list_project_calculations", lambda *_a, **_k: ())
    timings: dict[str, float] = {}

    project_tree_module.build_project_tree(
        tmp_path,
        project.id,
        include_sections={"calculations"},
        section_timings_ms=timings,
    )

    assert {"project", "calculations", "labels"}.issubset(timings)
    assert "wells" not in timings
    assert "exports" not in timings
    assert all(value >= 0.0 for value in timings.values())


def test_navigation_cache_reports_profile_hits_and_branch_timings(tmp_path: Path) -> None:
    project_dir = tmp_path / "p1"
    project_dir.mkdir()
    (project_dir / "project.json").write_text('{"id":"p1"}', encoding="utf-8")
    cache = ProjectNavigationRuntimeCache(max_projects=2)

    cold = cache.lookup(tmp_path, "p1", profile="calculations")
    cache.store(
        project_id="p1",
        token=cold.token,
        tree=({"id": "project:p1"},),
        counts={"calculations": 2},
        metadata_files=cold.metadata_files,
        profile="calculations",
        load_ms=12.5,
        branch_timings_ms={"project": 1.0, "calculations": 8.5, "labels": 0.5},
    )
    assert cache.lookup(tmp_path, "p1", profile="calculations").hit

    snapshot = cache.snapshot()
    profile = snapshot["profiles"]["calculations"]
    assert profile["misses"] == 1
    assert profile["hits"] == 1
    assert profile["loads"] == 1
    assert profile["last_load_ms"] == 12.5
    assert profile["branch_timings_ms"]["calculations"] == 8.5
    assert snapshot["latest_branch_timings_ms"]["labels"] == 0.5
