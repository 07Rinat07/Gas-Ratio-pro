from copy import deepcopy

from services.visualization_render_validation import VisualizationRenderValidationPipeline
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload():
    return {
        "source_type": "las",
        "source_id": "render-validation",
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


def _pipeline():
    return VisualizationScenePipeline().run(_payload()).to_dict()


def test_render_validation_accepts_valid_pipeline_geometry():
    pipeline = _pipeline()
    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
    assert report["ok"] is True
    assert report["canvas_ok"] is True
    assert report["clips_ok"] is True
    assert report["primitives_ok"] is True
    assert report["labels_ok"] is True
    assert report["page_layout_ok"] is True
    assert report["issues"] == []


def test_scene_pipeline_exposes_pre_render_validation_result():
    pipeline = _pipeline()
    assert pipeline["validation"]["render_validation_ok"] is True
    assert pipeline["validation"]["render_validation"]["renderer_neutral"] is True


def test_render_validation_rejects_clip_outside_canvas():
    pipeline = deepcopy(_pipeline())
    pipeline["render_model"]["clip_regions"][0]["x"] = pipeline["render_model"]["width"] + 1
    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
    assert report["ok"] is False
    assert any("clip_outside_canvas" in issue for issue in report["issues"])


def test_render_validation_rejects_unclipped_primitive_outside_canvas():
    pipeline = deepcopy(_pipeline())
    canvas = next(item for item in pipeline["render_model"]["primitives"] if item["id"] == "canvas.background")
    canvas["payload"]["width"] = pipeline["render_model"]["width"] + 10
    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
    assert report["ok"] is False
    assert "render_validation_primitive_outside_canvas:canvas.background" in report["issues"]


def test_render_validation_detects_high_level_label_overlap():
    pipeline = deepcopy(_pipeline())
    labels = [item for item in pipeline["render_model"]["primitives"] if item["kind"] == "text" and item["payload"].get("data_kind") in {"curve_label", "track_title"}]
    labels[1]["payload"]["x"] = labels[0]["payload"]["x"]
    labels[1]["payload"]["y"] = labels[0]["payload"]["y"]
    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
    assert report["ok"] is False
    assert any("label_overlap" in issue for issue in report["issues"])


def test_render_validation_rejects_content_outside_printable_page():
    pipeline = deepcopy(_pipeline())
    pipeline["print_layout"]["pages"][0]["content_bounds"]["x"] = 0
    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
    assert report["ok"] is False
    assert "render_validation_content_outside_printable:1" in report["issues"]
