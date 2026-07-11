from __future__ import annotations

import pytest

from services.las_viewer_multitrack_builder import LasViewerMultiTrackBuilder
from services.las_viewer_open_workflow import LasViewerOpenWorkflow


def _payload():
    return {
        "project_id": "project-1",
        "las_id": "well-a.las",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1002.0},
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "width": 1.2},
            {"id": "track.gas", "title": "Gas", "width": 1.0},
            {"id": "track.other", "title": "Other", "width": 1.0},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma", "points": [{"depth": 1000, "value": 10}, {"depth": 1001, "value": 20}]},
            {"mnemonic": "TG", "track_id": "track.gas", "points": [[1000, 1], [1001, 2]]},
            {"mnemonic": "EMPTY", "track_id": "track.other", "points": []},
            {"mnemonic": "NULL", "track_id": "track.other", "points": [{"depth": 1000, "value": None}]},
        ],
    }


def test_builds_complete_multitrack_viewer_and_excludes_empty_curves():
    result = LasViewerMultiTrackBuilder().build(_payload())

    assert result.ok is True
    assert result.track_count == 2
    assert result.curve_count == 2
    assert result.excluded_curves == ("EMPTY", "NULL")
    assert [item["id"] for item in result.payload["tracks"]] == ["track.gamma", "track.gas"]
    assert result.payload["tracks"][0]["curve_ids"] == ["GR"]
    assert result.viewer_state["visible_tracks"] == ["track.gamma", "track.gas"]
    assert result.render_result["profile"]["rendered_curve_count"] == 2
    assert result.to_dict()["raw_dataframe_included"] is False


def test_missing_track_descriptor_is_created_deterministically():
    payload = _payload()
    payload["curves"].append({"mnemonic": "CUSTOM", "track_id": "track.custom", "points": [[1000, 3], [1001, 4]]})

    result = LasViewerMultiTrackBuilder().build(payload)

    assert result.payload["tracks"][-1]["id"] == "track.custom"
    assert result.payload["tracks"][-1]["curve_ids"] == ["CUSTOM"]


def test_all_empty_curves_are_rejected():
    payload = _payload()
    payload["curves"] = [{"mnemonic": "EMPTY", "track_id": "track.other", "points": []}]

    with pytest.raises(ValueError, match="renderable curves"):
        LasViewerMultiTrackBuilder().build(payload)


def test_real_open_payload_builds_multitrack_viewer(tmp_path):
    opened = LasViewerOpenWorkflow(tmp_path).open("project-1", "examples/sample_gas_data.las")

    result = LasViewerMultiTrackBuilder().build(opened.payload)

    assert result.ok is True
    assert result.track_count >= 1
    assert result.curve_count == opened.curve_count
    assert result.viewer_state["las_id"] == opened.las_id
    assert result.render_result["viewport_result"]["pipeline"]["render_model"]["schema"] == "visualization.render.model"
