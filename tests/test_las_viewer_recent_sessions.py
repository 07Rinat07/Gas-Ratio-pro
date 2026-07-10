from __future__ import annotations

from services.las_viewer_recent_sessions import LasViewerRecentSessions
from services.las_viewer_session import LasViewerSession
from services.las_viewer_workspace_autosave_repository import LasViewerWorkspaceAutosaveRepository
from services.las_viewer_workspace_session_switcher import LasViewerWorkspaceSessionSwitcher


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


def test_recent_sessions_returns_valid_metadata(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    recent = LasViewerRecentSessions(repository).list()

    assert len(recent) == 1
    assert recent[0].project_id == "project-1"
    assert recent[0].las_id == "a.las"
    assert recent[0].valid is True
    assert len(recent[0].session_key) == 20


def test_recent_sessions_marks_active_identity(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("active.las"))

    recent = LasViewerRecentSessions(repository).list(
        active_project_id="project-1",
        active_las_id="active.las",
    )

    assert recent[0].active is True


def test_recent_sessions_limit_is_enforced(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))

    assert len(LasViewerRecentSessions(repository).list(limit=1)) == 1


def test_recent_sessions_rejects_invalid_limit(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)

    try:
        LasViewerRecentSessions(repository).list(limit=0)
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_latest_filters_by_las_identity(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))

    latest = LasViewerRecentSessions(repository).latest(las_id="a.las")

    assert latest is not None and latest.las_id == "a.las"


def test_snapshot_is_renderer_neutral(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))

    snapshot = LasViewerRecentSessions(repository).snapshot()

    assert snapshot["schema"] == "las.viewer.recent-sessions"
    assert snapshot["renderer_neutral"] is True
    assert snapshot["count"] == 1


def test_repository_recovers_selected_entry(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("selected.las"))
    filename = repository.entries()[0].filename

    recovery = repository.recover_entry(filename)

    assert recovery.recovered is True
    assert recovery.state is not None and recovery.state.las_id == "selected.las"


def test_repository_rejects_unsafe_selected_entry(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)

    recovery = repository.recover_entry("../outside.autosave.json")

    assert recovery.recovered is False
    assert recovery.reason == "invalid_repository_filename"


def test_switcher_activates_selected_recent_entry(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("saved.las"))
    filename = repository.entries()[0].filename
    switcher = LasViewerWorkspaceSessionSwitcher(repository, active_session=_session("current.las"))

    result = switcher.recover_entry_and_activate(filename)

    assert result.switched is True
    assert result.recovered is True
    assert switcher.active_state is not None and switcher.active_state.las_id == "saved.las"
