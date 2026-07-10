from __future__ import annotations

import os

from services.las_viewer_session import LasViewerSession
from services.las_viewer_workspace_autosave_repository import LasViewerWorkspaceAutosaveRepository


def _session(las_id: str, project_id: str = "project-1") -> LasViewerSession:
    return LasViewerSession({
        "project_id": project_id,
        "las_id": las_id,
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1200.0},
        "tracks": [{"id": "gamma"}],
        "curves": [{"mnemonic": "GR", "track_id": "gamma"}],
        "visible_tracks": ["gamma"],
    })


def test_repository_saves_independent_sessions_and_lists_them(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))

    entries = repository.entries()

    assert len(entries) == 2
    assert {item.las_id for item in entries} == {"a.las", "b.las"}
    assert all(item.valid for item in entries)


def test_recover_latest_returns_newest_compatible_session(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))
    b_path = next(tmp_path.glob("*b.las*"))
    os.utime(b_path, ns=(b_path.stat().st_atime_ns, b_path.stat().st_mtime_ns + 10_000))

    result = repository.recover_latest(project_id="project-1")

    assert result.recovered is True
    assert result.state is not None and result.state.las_id == "b.las"


def test_recover_latest_filters_by_las_id(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))

    recovered = repository.recover_latest_session(las_id="a.las")

    assert recovered is not None
    assert recovered.state.las_id == "a.las"


def test_corrupt_newest_autosave_is_skipped(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("valid.las"))
    repository.save(_session("broken.las"))
    broken = next(tmp_path.glob("*broken.las*.json"))
    broken.write_text("{broken", encoding="utf-8")
    os.utime(broken, ns=(broken.stat().st_atime_ns, broken.stat().st_mtime_ns + 10_000))

    result = repository.recover_latest()

    assert result.recovered is True
    assert result.state is not None and result.state.las_id == "valid.las"
    assert result.skipped_invalid == 1


def test_prune_keeps_newest_stores(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path, max_entries=2)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))
    repository.save(_session("c.las"))

    entries = repository.entries()

    assert len(entries) == 2
    assert "a.las" not in {item.las_id for item in entries}


def test_clear_removes_all_repository_files(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))

    removed = repository.clear()

    assert removed == 2
    assert repository.entries() == ()


def test_invalid_max_entries_is_rejected(tmp_path):
    try:
        LasViewerWorkspaceAutosaveRepository(tmp_path, max_entries=0)
    except ValueError as exc:
        assert "max_entries" in str(exc)
    else:
        raise AssertionError("expected ValueError")
