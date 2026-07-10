from __future__ import annotations

import pytest

from services.las_viewer_interaction_overlay import LasViewerInteractionOverlayEngine
from services.visualization_cursor import CursorReadout
from services.visualization_interaction_session import InteractionSessionState
from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_render_model import RenderClipRegion, RenderPrimitive, VisualizationRenderModel
from services.visualization_selection import SelectionItem, SelectionState


def _model():
    return VisualizationRenderModel(
        width=400,
        height=600,
        clip_regions=(
            RenderClipRegion("clip.track.a.plot", 0, 50, 180, 500),
            RenderClipRegion("clip.track.b.plot", 200, 50, 180, 500),
        ),
        primitives=(
            RenderPrimitive(
                id="curve.a",
                kind="polyline",
                z_index=30,
                track_id="track.a",
                clip_id="clip.track.a.plot",
                payload={"points": [[0, 50], [180, 550]], "source_layer_id": "curve.gamma"},
            ),
            RenderPrimitive(
                id="curve.b",
                kind="polyline",
                z_index=30,
                track_id="track.b",
                clip_id="clip.track.b.plot",
                payload={"points": [[200, 50], [380, 550]], "source_layer_id": "curve.gamma"},
            ),
        ),
    )


def _state(with_cursor=True, with_selection=True):
    viewport = InteractiveViewport(1000, 1100, 50, 550, inverted=True, unit="M")
    cursor = CursorReadout(100, 300, 1050, "M", "track.a") if with_cursor else None
    selection = SelectionState(
        items=(SelectionItem("curve.a", "polyline", "track.a", "curve.gamma"),),
        revision=1,
    ) if with_selection else SelectionState()
    return InteractionSessionState(viewport, selection, cursor, revision=2)


def test_combines_cursor_and_selection_overlays():
    result = LasViewerInteractionOverlayEngine().resolve(_model(), _state())
    ids = {item.id for item in result.primitives}
    assert ids == {"selection.curve.a", "selection.curve.b", "cursor.track.a", "cursor.track.b"}


def test_cursor_overlays_are_non_printable_lines():
    result = LasViewerInteractionOverlayEngine().resolve(_model(), _state())
    cursors = [item for item in result.primitives if item.payload.get("cursor_overlay")]
    assert len(cursors) == 2
    assert all(item.kind == "line" and item.printable is False for item in cursors)
    assert all(item.payload["depth"] == 1050 for item in cursors)


def test_track_filter_limits_both_overlay_types():
    result = LasViewerInteractionOverlayEngine().resolve(
        _model(), _state(), track_ids=("track.b",)
    )
    assert {item.track_id for item in result.primitives} == {"track.b"}


def test_no_cursor_produces_only_selection_overlay():
    result = LasViewerInteractionOverlayEngine().resolve(_model(), _state(with_cursor=False))
    assert result.cursor is None
    assert all(not item.payload.get("cursor_overlay") for item in result.primitives)


def test_empty_interaction_returns_empty_overlay():
    result = LasViewerInteractionOverlayEngine().resolve(
        _model(), _state(with_cursor=False, with_selection=False)
    )
    assert result.empty


def test_apply_to_appends_primitives_and_metadata():
    model = _model()
    result = LasViewerInteractionOverlayEngine().resolve(model, _state())
    composed = result.apply_to(model)
    assert len(composed.primitives) == len(model.primitives) + len(result.primitives)
    assert composed.metadata["las_viewer_interaction_overlay"]["primitive_count"] == 4


def test_serialized_contracts_are_supported():
    result = LasViewerInteractionOverlayEngine().resolve(
        _model().to_dict(), _state().to_dict()
    )
    assert result.to_dict()["renderer_neutral"] is True


def test_empty_cursor_color_is_rejected():
    with pytest.raises(ValueError):
        LasViewerInteractionOverlayEngine().resolve(_model(), _state(), cursor_color=" ")
