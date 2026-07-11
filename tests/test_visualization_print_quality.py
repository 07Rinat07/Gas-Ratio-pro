from copy import deepcopy

from services.visualization_print_quality import VisualizationPrintQualityValidator
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _pipeline():
    payload = {
        "source_type": "las",
        "source_id": "print-quality",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1002.0, "step": 1.0},
        "tracks": [{"id": "track.gamma", "title": "Gamma", "width": 1.0}],
        "curves": [{
            "id": "curve.GR",
            "track_id": "track.gamma",
            "mnemonic": "GR",
            "unit": "API",
            "scale_type": "linear",
            "range": {"min": 0, "max": 150},
            "points": [
                {"depth": 1000.0, "value": 45.0},
                {"depth": 1001.0, "value": 60.0},
                {"depth": 1002.0, "value": 72.0},
            ],
        }],
        "overlays": [],
    }
    return VisualizationScenePipeline().run(payload).to_dict()


def test_print_quality_accepts_complete_engineering_render_model():
    report = VisualizationPrintQualityValidator().validate(_pipeline()).to_dict()
    assert report["ok"] is True
    assert report["curve_count"] == 1
    assert report["major_grid_count"] > 0
    assert report["minimum_font_size"] >= 7
    assert report["issues"] == []


def test_print_quality_rejects_thin_curve_and_small_font():
    pipeline = deepcopy(_pipeline())
    for primitive in pipeline["render_model"]["primitives"]:
        if primitive["kind"] == "polyline":
            primitive["payload"]["stroke_width"] = 0.2
        if primitive.get("payload", {}).get("data_kind") == "curve_label":
            primitive["payload"]["font_size"] = 5
    report = VisualizationPrintQualityValidator().validate(pipeline).to_dict()
    assert report["ok"] is False
    assert any("curve_stroke_too_thin" in issue for issue in report["issues"])
    assert any("font_too_small" in issue for issue in report["issues"])


def test_print_quality_rejects_curve_without_label():
    pipeline = deepcopy(_pipeline())
    pipeline["render_model"]["primitives"] = [
        primitive for primitive in pipeline["render_model"]["primitives"]
        if primitive.get("payload", {}).get("data_kind") != "curve_label"
    ]
    report = VisualizationPrintQualityValidator().validate(pipeline).to_dict()
    assert report["ok"] is False
    assert "print_quality_curve_label_missing:curve.GR" in report["issues"]


def test_print_quality_rejects_invalid_grid_hierarchy():
    pipeline = deepcopy(_pipeline())
    for primitive in pipeline["render_model"]["primitives"]:
        if primitive["id"].startswith("grid.depth."):
            primitive["payload"]["stroke_width"] = 0.4 if primitive["payload"].get("major") else 0.8
    report = VisualizationPrintQualityValidator().validate(pipeline).to_dict()
    assert report["ok"] is False
    assert "print_quality_grid_hierarchy_invalid" in report["issues"]
