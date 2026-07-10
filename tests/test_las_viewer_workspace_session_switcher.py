from __future__ import annotations

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


def test_activate_switches_and_autosaves_previous(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    switcher = LasViewerWorkspaceSessionSwitcher(repository, active_session=_session("a.las"))

    result = switcher.activate(_session("b.las"))

    assert result.switched is True
    assert result.autosaved_previous is True
    assert switcher.active_state is not None and switcher.active_state.las_id == "b.las"
    assert repository.recover_latest_session(las_id="a.las") is not None


def test_failed_recovery_preserves_active_session(tmp_path):
    switcher = LasViewerWorkspaceSessionSwitcher(
        LasViewerWorkspaceAutosaveRepository(tmp_path),
        active_session=_session("active.las"),
    )

    result = switcher.recover_and_activate(las_id="missing.las")

    assert result.switched is False
    assert switcher.active_state is not None and switcher.active_state.las_id == "active.las"


def test_recover_and_activate_uses_matching_autosave(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("saved.las"))
    switcher = LasViewerWorkspaceSessionSwitcher(repository)

    result = switcher.recover_and_activate(project_id="project-1", las_id="saved.las")

    assert result.switched is True
    assert result.recovered is True
    assert switcher.active_state is not None and switcher.active_state.las_id == "saved.las"


def test_open_or_recover_does_not_call_factory_when_autosave_exists(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("saved.las"))
    switcher = LasViewerWorkspaceSessionSwitcher(repository)
    called = False

    def factory() -> LasViewerSession:
        nonlocal called
        called = True
        return _session("fresh.las")

    result = switcher.open_or_recover(factory, las_id="saved.las")

    assert result.recovered is True
    assert called is False


def test_open_or_recover_creates_fresh_session_when_missing(tmp_path):
    switcher = LasViewerWorkspaceSessionSwitcher(LasViewerWorkspaceAutosaveRepository(tmp_path))

    result = switcher.open_or_recover(lambda: _session("fresh.las"), las_id="fresh.las")

    assert result.switched is True
    assert result.recovered is False
    assert result.reason == "created_fresh_session"
    assert switcher.active_state is not None and switcher.active_state.las_id == "fresh.las"


def test_same_session_identity_is_not_added_as_switch(tmp_path):
    switcher = LasViewerWorkspaceSessionSwitcher(
        LasViewerWorkspaceAutosaveRepository(tmp_path),
        active_session=_session("same.las"),
    )

    result = switcher.activate(_session("same.las"))

    assert result.switched is False
    assert result.reason == "same_session"


def test_close_autosaves_and_clears_active_session(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    switcher = LasViewerWorkspaceSessionSwitcher(repository, active_session=_session("a.las"))

    result = switcher.close()

    assert result.switched is True
    assert result.autosaved_previous is True
    assert switcher.active_session is None
    assert repository.recover_latest_session(las_id="a.las") is not None


def test_close_without_active_session_is_noop(tmp_path):
    switcher = LasViewerWorkspaceSessionSwitcher(LasViewerWorkspaceAutosaveRepository(tmp_path))

    result = switcher.close()

    assert result.switched is False
    assert result.reason == "no_active_session"
