from __future__ import annotations

import pytest

from services.las_viewer_interaction_overlay import LasViewerInteractionOverlayStyle
from services.las_viewer_overlay_presets import (
    LasViewerOverlayPreset,
    LasViewerOverlayPresetRepository,
)
from services.las_viewer_overlay_runtime import (
    LasViewerOverlayPresetRuntime,
    LasViewerOverlayRuntimeState,
)
from services.las_viewer_session import LasViewerSession
from services.visualization_cursor import CursorReadout
from services.visualization_interaction_session import InteractionSessionState, VisualizationInteractionSession
from services.visualization_render_model import RenderClipRegion, RenderPrimitive, VisualizationRenderModel
from services.visualization_selection import SelectionItem, SelectionState


def _session() -> LasViewerSession:
    session = LasViewerSession(
        {
            "project_id": "project-a",
            "las_id": "well-a",
            "depth_unit": "M",
            "depth_range": {"start": 1000, "stop": 1100},
            "tracks": [{"id": "track.a"}],
            "curves": [{"mnemonic": "GR", "track_id": "track.a"}],
        },
        screen_start=50,
        screen_stop=550,
    )
    state = session.interaction_session.state
    session._interaction = VisualizationInteractionSession.from_state(
        InteractionSessionState(
            viewport=state.viewport,
            selection=SelectionState(
                items=(SelectionItem("curve.a", "polyline", "track.a", "curve.gamma"),),
                revision=1,
            ),
            cursor=CursorReadout(100, 300, 1050, "M", "track.a"),
            revision=2,
        )
    )
    return session


def _model() -> VisualizationRenderModel:
    return VisualizationRenderModel(
        width=200,
        height=600,
        clip_regions=(RenderClipRegion("clip.track.a.plot", 0, 50, 180, 500),),
        primitives=(
            RenderPrimitive(
                id="curve.a",
                kind="polyline",
                z_index=30,
                track_id="track.a",
                clip_id="clip.track.a.plot",
                payload={"points": [[0, 50], [180, 550]], "source_layer_id": "curve.gamma"},
            ),
        ),
    )


def _repository(width: float = 1.0) -> LasViewerOverlayPresetRepository:
    repository = LasViewerOverlayPresetRepository.with_defaults()
    repository.save(
        LasViewerOverlayPreset(
            "Field",
            LasViewerInteractionOverlayStyle(cursor_color="#123456", cursor_width=width),
        )
    )
    return repository


def test_runtime_applies_named_preset() -> None:
    runtime = LasViewerOverlayPresetRuntime(_session(), _repository())
    state = runtime.apply("Field")
    assert state.active_preset == "Field"
    assert state.style.cursor_color == "#123456"
    assert state.revision == 1


def test_runtime_resolves_overlay_using_active_style() -> None:
    runtime = LasViewerOverlayPresetRuntime(_session(), _repository(), active_preset="Field")
    overlay = runtime.resolve_overlay(_model())
    cursor = next(item for item in overlay.primitives if item.payload.get("cursor_overlay"))
    assert cursor.payload["stroke"] == "#123456"


def test_runtime_hot_reload_updates_active_style() -> None:
    runtime = LasViewerOverlayPresetRuntime(_session(), _repository(1.0), active_preset="Field")
    state = runtime.synchronize(_repository(3.0))
    assert state.active_preset == "Field"
    assert state.style.cursor_width == 3.0
    assert state.revision == 1


def test_runtime_hot_reload_is_noop_for_same_repository() -> None:
    repository = _repository()
    runtime = LasViewerOverlayPresetRuntime(_session(), repository, active_preset="Field")
    before = runtime.state
    after = runtime.synchronize(repository)
    assert after == before


def test_runtime_falls_back_when_active_preset_disappears() -> None:
    runtime = LasViewerOverlayPresetRuntime(_session(), _repository(), active_preset="Field")
    state = runtime.synchronize(LasViewerOverlayPresetRepository.with_defaults())
    assert state.active_preset == "Default"
    assert state.fallback_applied is True
    assert state.revision == 1


def test_runtime_snapshot_round_trip() -> None:
    runtime = LasViewerOverlayPresetRuntime(_session(), _repository(), active_preset="Field")
    snapshot = runtime.snapshot()
    restored = LasViewerOverlayRuntimeState.from_dict(snapshot)
    assert restored.active_preset == "Field"
    assert restored.repository_fingerprint
    assert restored.to_dict()["renderer_neutral"] is True


def test_runtime_restore_rejects_another_las_session() -> None:
    runtime = LasViewerOverlayPresetRuntime(_session(), _repository())
    payload = runtime.snapshot()
    payload["las_id"] = "other-well"
    with pytest.raises(ValueError, match="another LAS session"):
        runtime.restore(payload)


def test_runtime_unknown_preset_is_rejected() -> None:
    runtime = LasViewerOverlayPresetRuntime(_session(), _repository())
    with pytest.raises(KeyError):
        runtime.apply("Unknown")


def test_runtime_restores_and_updates_workspace_active_preset() -> None:
    from core.workspace_session import SESSION_ACTIVE_OVERLAY_PRESET_KEY

    workspace_state = {SESSION_ACTIVE_OVERLAY_PRESET_KEY: "Field"}
    runtime = LasViewerOverlayPresetRuntime(
        _session(),
        _repository(),
        workspace_state=workspace_state,
    )

    assert runtime.active_preset == "Field"

    runtime.apply("Default")
    assert workspace_state[SESSION_ACTIVE_OVERLAY_PRESET_KEY] == "Default"


def test_runtime_updates_workspace_state_after_fallback() -> None:
    from core.workspace_session import SESSION_ACTIVE_OVERLAY_PRESET_KEY

    workspace_state = {SESSION_ACTIVE_OVERLAY_PRESET_KEY: "Field"}
    runtime = LasViewerOverlayPresetRuntime(
        _session(),
        _repository(),
        workspace_state=workspace_state,
    )

    runtime.synchronize(LasViewerOverlayPresetRepository.with_defaults())

    assert runtime.active_preset == "Default"
    assert workspace_state[SESSION_ACTIVE_OVERLAY_PRESET_KEY] == "Default"
