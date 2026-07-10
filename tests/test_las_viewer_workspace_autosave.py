from __future__ import annotations

import json

from services.las_viewer_session import LasViewerSession
from services.las_viewer_workspace_autosave import LasViewerWorkspaceAutosaveStore
from services.visualization_viewport_controller import ViewportCommand


def _payload(las_id="well-a.las"):
    return {
        "project_id": "project-1",
        "las_id": las_id,
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1200.0},
        "tracks": [{"id": "gamma"}, {"id": "gas"}],
        "curves": [{"mnemonic": "GR", "track_id": "gamma"}, {"mnemonic": "TG", "track_id": "gas"}],
        "visible_tracks": ["gamma", "gas"],
    }


def test_autosave_round_trip_restores_compact_viewer_state(tmp_path):
    source = LasViewerSession(_payload())
    source.layout_controller.set_track_width("gas", 2.0)
    source.interaction_session.execute_viewport(ViewportCommand.zoom(2.0))
    store = LasViewerWorkspaceAutosaveStore(tmp_path)

    saved = store.save(source)
    recovered = store.recover_session(project_id="project-1", las_id="well-a.las")

    assert saved.written is True
    assert recovered is not None
    assert recovered.state == source.state


def test_unchanged_state_is_not_rewritten(tmp_path):
    session = LasViewerSession(_payload())
    store = LasViewerWorkspaceAutosaveStore(tmp_path)
    store.save(session)
    before = store.path.stat().st_mtime_ns

    result = store.save(session)

    assert result.written is False
    assert result.reason == "unchanged"
    assert store.path.stat().st_mtime_ns == before


def test_previous_autosave_becomes_backup(tmp_path):
    store = LasViewerWorkspaceAutosaveStore(tmp_path)
    first = LasViewerSession(_payload("first.las"))
    second = LasViewerSession(_payload("second.las"))

    store.save(first)
    store.save(second)

    assert store.backup_path.exists()
    backup = store._load_state(store.backup_path)[0]
    assert backup.las_id == "first.las"


def test_corrupt_primary_recovers_valid_backup(tmp_path):
    store = LasViewerWorkspaceAutosaveStore(tmp_path)
    first = LasViewerSession(_payload("first.las"))
    second = LasViewerSession(_payload("second.las"))
    store.save(first)
    store.save(second)
    store.path.write_text("{broken", encoding="utf-8")

    result = store.recover(las_id="first.las")

    assert result.recovered is True
    assert result.used_backup is True
    assert result.state is not None and result.state.las_id == "first.las"


def test_checksum_tampering_is_rejected(tmp_path):
    store = LasViewerWorkspaceAutosaveStore(tmp_path)
    store.save(LasViewerSession(_payload()))
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    raw["state"]["las_id"] = "tampered.las"
    store.path.write_text(json.dumps(raw), encoding="utf-8")

    result = store.recover()

    assert result.recovered is False
    assert "checksum_mismatch" in result.reason


def test_context_mismatch_is_rejected(tmp_path):
    store = LasViewerWorkspaceAutosaveStore(tmp_path)
    store.save(LasViewerSession(_payload()))

    assert store.recover(project_id="other").recovered is False
    assert store.recover(las_id="other.las").recovered is False


def test_clear_removes_primary_and_backup(tmp_path):
    store = LasViewerWorkspaceAutosaveStore(tmp_path)
    store.save(LasViewerSession(_payload("first.las")))
    store.save(LasViewerSession(_payload("second.las")))

    assert store.clear() == 2
    assert store.clear() == 0


def test_filename_rejects_paths(tmp_path):
    try:
        LasViewerWorkspaceAutosaveStore(tmp_path, filename="nested/state.json")
    except ValueError as exc:
        assert "simple file name" in str(exc)
    else:
        raise AssertionError("expected ValueError")
