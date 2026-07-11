from services.las_viewer_curve_validation import LasViewerCurveValidator
from services.las_viewer_multitrack_builder import LasViewerMultiTrackBuilder


def test_excludes_empty_and_all_null_curves_but_keeps_partial_curve():
    curves = [
        {"mnemonic": "EMPTY", "points": []},
        {"mnemonic": "NULL", "points": [[1000, None], [1001, float("nan")]]},
        {"mnemonic": "GR", "unit": "API", "points": [[1000, 10], [1001, None], [1002, 20]]},
    ]
    result = LasViewerCurveValidator().validate(curves)

    assert result.excluded_curves == ("EMPTY", "NULL")
    assert [item["mnemonic"] for item in result.curves] == ["GR"]
    assert result.curves[0]["unit"] == "api"
    assert result.curves[0]["quality"]["null_sample_count"] == 1
    assert result.null_intervals["GR"] == ({"start": 1001.0, "stop": 1001.0, "sample_count": 1.0},)
    assert {item.code for item in result.diagnostics} >= {"curve_empty", "curve_all_null", "curve_partial_null"}


def test_invalid_depth_samples_are_removed_and_diagnosed():
    result = LasViewerCurveValidator().validate([
        {"mnemonic": "TG", "points": [[None, 1], [1000, 2], ["bad", 3]]},
    ])

    assert result.curves[0]["points"] == [[1000, 2]]
    assert result.curves[0]["quality"]["invalid_depth_sample_count"] == 2
    assert any(item.code == "curve_invalid_depth_samples" for item in result.diagnostics)


def test_unsupported_unit_is_nonfatal_and_normalized_to_unknown():
    result = LasViewerCurveValidator().validate([
        {"mnemonic": "CUSTOM", "unit": "bananas/fortnight", "points": [[1000, 1], [1001, 2]]},
    ])

    assert result.has_errors is False
    assert result.curves[0]["unit"] == "unknown"
    assert result.curves[0]["quality"]["unit_status"] == "unknown"
    assert result.diagnostics[0].code == "curve_unit_unsupported"


def test_builder_preserves_track_layout_after_excluding_bad_curves():
    payload = {
        "project_id": "project-1",
        "las_id": "well.las",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1002.0},
        "tracks": [
            {"id": "track.gamma", "title": "Gamma", "width": 1.4},
            {"id": "track.other", "title": "Other", "width": 1.0},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma", "unit": "API", "points": [[1000, 10], [1001, None], [1002, 20]]},
            {"mnemonic": "EMPTY", "track_id": "track.other", "points": []},
        ],
    }
    result = LasViewerMultiTrackBuilder().build(payload)

    assert result.ok is True
    assert result.track_count == 1
    assert result.payload["tracks"][0]["id"] == "track.gamma"
    assert result.payload["tracks"][0]["width"] == 1.4
    assert result.payload["curves"][0]["quality"]["null_sample_count"] == 1
    assert result.payload["null_intervals"]["GR"][0]["start"] == 1001.0
    assert "curve_partial_null" in result.diagnostics
    assert result.to_dict()["raw_dataframe_included"] is False
