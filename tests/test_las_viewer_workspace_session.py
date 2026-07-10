from __future__ import annotations

from core.application_state import ACTIVE_LAS_ID_KEY, ACTIVE_PROJECT_ID_KEY
from core.workspace_session import SESSION_LAS_VIEWER_STATE_KEY, WorkspaceSessionManager
from services.las_viewer_session import LasViewerSession
from services.las_viewer_workspace_session import LasViewerWorkspaceSessionBridge
from services.visualization_selection import SelectionCommand, SelectionItem
from services.visualization_viewport_controller import ViewportCommand


def _payload():
    return {
        "project_id": "project-1",
        "las_id": "well-a.las",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1200.0},
        "tracks": [{"id": "gamma"}, {"id": "gas"}],
        "curves": [
            {"mnemonic": "GR", "track_id": "gamma"},
            {"mnemonic": "TG", "track_id": "gas"},
            {"mnemonic": "C1", "track_id": "gas"},
        ],
        "visible_tracks": ["gamma", "gas"],
    }


def _state():
    return {ACTIVE_PROJECT_ID_KEY: "project-1", ACTIVE_LAS_ID_KEY: "well-a.las"}


def test_bridge_stores_complete_compact_viewer_state():
    workspace = _state()
    session = LasViewerSession(_payload())
    session.layout_controller.set_track_width("gas", 2.0)
    session.interaction_session.execute_viewport(ViewportCommand.zoom(2.0))
    session.interaction_session.execute_selection(SelectionCommand(mode="replace", items=(SelectionItem(primitive_id="curve:TG", source_layer_id="TG", data_kind="curve"),)))

    result = LasViewerWorkspaceSessionBridge(workspace).store(session)

    assert result.stored is True
    stored = workspace[SESSION_LAS_VIEWER_STATE_KEY]
    assert stored["layout"]["tracks"][1]["width"] == 2.0
    assert stored["interaction"]["viewport"]["domain_span"] == 100.0
    assert stored["interaction"]["selection"]["items"][0]["primitive_id"] == "curve:TG"


def test_bridge_restores_layout_viewport_selection_and_curve_mapping():
    workspace = _state()
    source = LasViewerSession(_payload())
    source.layout_controller.move_track("gas", 0)
    source.layout_controller.set_curve_visible("C1", False)
    source.activate_curve("TG")
    source.interaction_session.execute_viewport(ViewportCommand.zoom(2.0))
    source.interaction_session.execute_selection(SelectionCommand(mode="replace", items=(SelectionItem(primitive_id="curve:TG", source_layer_id="TG", data_kind="curve"),)))
    bridge = LasViewerWorkspaceSessionBridge(workspace)
    bridge.store(source)

    restored = bridge.restore_session()

    assert restored is not None
    assert restored.state.layout == source.state.layout
    assert restored.state.interaction == source.state.interaction
    assert restored.state.active_curve_id == "TG"
    assert restored.activate_curve("C1").active_track_id == "gas"


def test_bridge_rejects_wrong_active_las_context():
    workspace = _state()
    bridge = LasViewerWorkspaceSessionBridge(workspace)
    bridge.store(LasViewerSession(_payload()))
    workspace[ACTIVE_LAS_ID_KEY] = "other.las"

    result = bridge.restore()

    assert result.restored is False
    assert result.reason == "las_mismatch"


def test_bridge_can_restore_without_active_context_check():
    workspace = _state()
    bridge = LasViewerWorkspaceSessionBridge(workspace)
    bridge.store(LasViewerSession(_payload()))
    workspace[ACTIVE_PROJECT_ID_KEY] = "other-project"

    assert bridge.restore_session(require_active_context=False) is not None


def test_bridge_handles_missing_and_invalid_state():
    workspace = _state()
    bridge = LasViewerWorkspaceSessionBridge(workspace)
    assert bridge.restore().reason == "missing_state"

    workspace[SESSION_LAS_VIEWER_STATE_KEY] = {"schema": "broken"}
    assert bridge.restore().reason == "invalid_state"


def test_bridge_clear_removes_saved_viewer_state():
    workspace = _state()
    bridge = LasViewerWorkspaceSessionBridge(workspace)
    bridge.store(LasViewerSession(_payload()))

    assert bridge.clear() is True
    assert bridge.clear() is False


def test_workspace_manager_round_trip_preserves_las_viewer_state(tmp_path):
    source_state = _state()
    LasViewerWorkspaceSessionBridge(source_state).store(LasViewerSession(_payload()))
    source_manager = WorkspaceSessionManager(source_state, sessions_dir=tmp_path)
    path = tmp_path / "session.json"
    source_manager.save(path)

    target_state = {}
    target_manager = WorkspaceSessionManager(target_state, sessions_dir=tmp_path)
    target_manager.load_and_restore(path)

    restored = LasViewerWorkspaceSessionBridge(target_state).restore_session()
    assert restored is not None
    assert restored.state.las_id == "well-a.las"
    assert SESSION_LAS_VIEWER_STATE_KEY in target_manager.restore(target_manager.capture()).affected_keys
