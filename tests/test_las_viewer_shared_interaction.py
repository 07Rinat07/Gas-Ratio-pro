from __future__ import annotations

from services.las_viewer_multitrack_builder import LasViewerMultiTrackBuilder
from services.las_viewer_shared_interaction import LasViewerSharedInteractionController
from services.visualization_cursor import CursorRequest
from services.visualization_selection import SelectionCommand, SelectionItem
from services.visualization_viewport_controller import ViewportCommand


def _payload():
    return {
        "project_id": "project-1",
        "las_id": "well-a.las",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1100.0},
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "width": 1.0},
            {"id": "track.gas", "title": "Gas", "width": 1.0},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma", "points": [[1000, 10], [1050, 20], [1100, 30]]},
            {"mnemonic": "TG", "track_id": "track.gas", "points": [[1000, 1], [1050, 2], [1100, 3]]},
        ],
    }


def _controller():
    prepared = LasViewerMultiTrackBuilder().build(_payload()).payload
    return LasViewerSharedInteractionController(prepared)


def test_one_depth_viewport_drives_all_visible_tracks():
    controller = _controller()
    result = controller.execute_viewport(ViewportCommand.set_range(1020, 1080, source="test"))

    state = result.viewer_state["interaction"]["viewport"]
    assert state["domain_start"] == 1020.0
    assert state["domain_stop"] == 1080.0
    assert result.to_dict()["shared_depth_viewport"] == state
    assert result.to_dict()["visible_tracks"] == ["track.gamma", "track.gas"]
    assert result.render_model.metadata["las_viewer_shared_interaction"]["visible_track_count"] == 2


def test_cursor_is_synchronized_across_all_visible_track_regions():
    controller = _controller()
    initial = controller.render()
    region = next(item for item in initial.render_model.clip_regions if item.id == "clip.track.gamma.plot")
    result = controller.update_cursor(CursorRequest(x=region.x + 2, y=region.y + region.height / 2))

    cursor_lines = [item for item in result.overlay.primitives if item.payload.get("cursor_overlay")]
    assert {item.track_id for item in cursor_lines} == {"track.gamma", "track.gas"}
    assert len({item.payload["depth"] for item in cursor_lines}) == 1
    assert all(item.printable is False for item in cursor_lines)


def test_selection_overlay_uses_one_logical_selection_for_visible_tracks():
    controller = _controller()
    initial = controller.render()
    source = next(item for item in initial.render_model.primitives if item.id == "track.track.gamma.border")
    source_layer = source.payload.get("source_layer_id", "")
    command = SelectionCommand(
        mode="replace",
        items=(SelectionItem(
            primitive_id=source.id,
            primitive_kind=source.kind,
            track_id=source.track_id,
            source_layer_id=source_layer,
        ),),
        source="test",
    )

    result = controller.execute_selection(command)

    assert result.viewer_state["interaction"]["selection"]["selected_ids"] == [source.id]
    assert result.overlay.selection.selected_ids == (source.id,)
    assert all(item.printable is False for item in result.overlay.selection.primitives)


def test_viewport_change_clears_cursor_but_preserves_selection():
    controller = _controller()
    initial = controller.render()
    region = next(item for item in initial.render_model.clip_regions if item.id == "clip.track.gamma.plot")
    cursor = controller.update_cursor(CursorRequest(x=region.x + 2, y=region.y + 10))
    primitive = next(item for item in cursor.render_model.primitives if item.id == "track.track.gamma.border")
    controller.execute_selection(SelectionCommand(
        mode="replace",
        items=(SelectionItem(primitive_id=primitive.id, primitive_kind=primitive.kind, track_id=primitive.track_id),),
    ))

    result = controller.execute_viewport(ViewportCommand.zoom(2.0, source="test"))

    assert result.viewer_state["interaction"]["cursor"] is None
    assert result.viewer_state["interaction"]["selection"]["selected_ids"] == [primitive.id]
    assert result.overlay.cursor is None


def test_contract_is_renderer_neutral_and_does_not_include_dataframe():
    result = _controller().render().to_dict()

    assert result["renderer_neutral"] is True
    assert result["raw_dataframe_included"] is False
    assert result["render_model"]["schema"] == "visualization.render.model"
