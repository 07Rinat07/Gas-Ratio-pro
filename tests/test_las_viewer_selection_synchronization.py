from __future__ import annotations

from services.las_viewer_selection_synchronization import LasViewerSelectionSynchronizationEngine
from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel
from services.visualization_selection import SelectionItem, SelectionState


def _model():
    return VisualizationRenderModel(
        width=600,
        height=800,
        primitives=(
            RenderPrimitive(
                id="curve.gamma.left",
                kind="polyline",
                z_index=30,
                track_id="track.left",
                clip_id="clip.track.left.plot",
                payload={"points": [[1, 2], [3, 4]], "source_layer_id": "curve.gamma", "stroke_width": 1},
            ),
            RenderPrimitive(
                id="curve.gamma.right",
                kind="polyline",
                z_index=30,
                track_id="track.right",
                clip_id="clip.track.right.plot",
                payload={"points": [[10, 20], [30, 40]], "source_layer_id": "curve.gamma"},
            ),
            RenderPrimitive(
                id="curve.gas.right",
                kind="polyline",
                z_index=30,
                track_id="track.right",
                payload={"points": [[5, 6], [7, 8]], "source_layer_id": "curve.gas"},
            ),
        ),
    )


def _selection():
    return SelectionState(
        items=(
            SelectionItem(
                primitive_id="curve.gamma.left",
                primitive_kind="polyline",
                track_id="track.left",
                source_layer_id="curve.gamma",
            ),
        ),
        revision=1,
    )


def test_synchronizes_selected_source_layer_across_tracks():
    result = LasViewerSelectionSynchronizationEngine().resolve(_model(), _selection())
    assert result.synchronized_primitive_ids == (
        "selection.curve.gamma.left",
        "selection.curve.gamma.right",
    )
    assert all(item.payload["selection_overlay"] for item in result.primitives)


def test_can_disable_cross_track_source_synchronization():
    result = LasViewerSelectionSynchronizationEngine().resolve(
        _model(), _selection(), synchronize_source_layers=False
    )
    assert result.synchronized_primitive_ids == ("selection.curve.gamma.left",)


def test_track_filter_limits_overlay_targets():
    result = LasViewerSelectionSynchronizationEngine().resolve(
        _model(), _selection(), track_ids=("track.right",)
    )
    assert result.synchronized_primitive_ids == ("selection.curve.gamma.right",)


def test_overlay_is_non_printable_and_above_original():
    result = LasViewerSelectionSynchronizationEngine().resolve(_model(), _selection())
    overlay = result.primitives[0]
    assert overlay.printable is False
    assert overlay.z_index == 230
    assert overlay.payload["stroke_width"] == 3.0


def test_missing_primitive_is_reported():
    state = SelectionState(items=(SelectionItem(primitive_id="missing"),))
    result = LasViewerSelectionSynchronizationEngine().resolve(_model(), state)
    assert result.empty
    assert "selection_overlay_missing_primitive:missing" in result.diagnostics


def test_missing_requested_track_is_reported():
    result = LasViewerSelectionSynchronizationEngine().resolve(
        _model(), _selection(), track_ids=("track.unknown",)
    )
    assert "selection_overlay_missing_track:track.unknown" in result.diagnostics


def test_serialized_contracts_are_supported():
    result = LasViewerSelectionSynchronizationEngine().resolve(
        _model().to_dict(), _selection().to_dict()
    )
    payload = result.to_dict()
    assert payload["schema"] == "las.viewer.selection-overlay"
    assert payload["renderer_neutral"] is True


def test_empty_selection_returns_empty_overlay():
    result = LasViewerSelectionSynchronizationEngine().resolve(_model(), SelectionState())
    assert result.empty
    assert not result.diagnostics


def test_empty_accent_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        LasViewerSelectionSynchronizationEngine().resolve(_model(), _selection(), accent=" ")
