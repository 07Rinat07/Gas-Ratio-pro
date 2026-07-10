from services.visualization_label_legend import VisualizationLabelLegendEngine


def test_label_legend_engine_builds_track_curve_and_interval_contracts():
    scene = {
        "tracks": [{"id": "track.gas", "title": "Gas Track"}],
        "layers": [
            {"id": "curve.C1", "kind": "curve", "track_id": "track.gas", "payload": {"mnemonic": "C1", "unit": "PPM", "style": {"stroke": "#ff0000"}}},
            {"id": "interval.gas", "kind": "interval_overlay", "track_id": "track.gas", "payload": {"label": "Gas", "confidence": 0.9, "style": {"fill": "#ffd54f"}}},
        ],
    }
    layout = {"tracks": [{"id": "track.gas", "header_bounds": {"x": 10, "y": 0, "width": 200, "height": 40}, "axis_bounds": {"x": 10, "y": 40, "width": 200, "height": 24}}]}

    result = VisualizationLabelLegendEngine().build(scene, layout).to_dict()

    assert result["ok"] is True
    assert any(item["kind"] == "track_title" for item in result["labels"])
    assert any(item["kind"] == "curve_label" and item["text"] == "C1 [PPM]" for item in result["labels"])
    assert any(item["kind"] == "curve" and item["color"] == "#ff0000" for item in result["legend_items"])
    assert any(item["kind"] == "interval" and item["label"] == "Gas" for item in result["legend_items"])
    assert result["metadata"]["raw_dataframe_included"] is False


def test_label_legend_engine_limits_curve_labels_per_track():
    scene = {
        "tracks": [{"id": "track.many", "title": "Many"}],
        "layers": [
            {"id": f"curve.C{i}", "kind": "curve", "track_id": "track.many", "payload": {"mnemonic": f"C{i}"}}
            for i in range(7)
        ],
    }
    layout = {"tracks": [{"id": "track.many", "header_bounds": {"x": 0, "y": 0, "width": 120, "height": 40}, "axis_bounds": {"x": 0, "y": 40, "width": 120, "height": 24}}]}

    result = VisualizationLabelLegendEngine().build(scene, layout).to_dict()

    assert result["metadata"]["curve_label_count"] == 4
    assert result["metadata"]["truncated_curve_label_count"] == 3
    assert "label_legend_curve_labels_truncated:track.many:3" in result["issues"]
