from __future__ import annotations

from services.visualization_renderer_parity import VisualizationRendererParityValidator
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


def _payload():
    return {
        "source_type": "las",
        "source_id": "parity-demo",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1001.0, "step": 1.0},
        "tracks": [{"id": "track.gamma", "title": "Gamma", "width": 1.0}],
        "curves": [
            {
                "id": "curve.GR",
                "track_id": "track.gamma",
                "mnemonic": "GR",
                "unit": "API",
                "scale_type": "linear",
                "range": {"min": 0, "max": 150},
                "points": [
                    {"depth": 1000.0, "value": 45.0},
                    {"depth": 1001.0, "value": 60.0},
                ],
            }
        ],
        "overlays": [],
    }


def test_svg_renderer_applies_print_layout_and_matches_render_model_counts():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    rendered = VisualizationSvgSceneRenderer().render(pipeline).to_dict()
    report = VisualizationRendererParityValidator().validate(pipeline, rendered).to_dict()

    assert rendered["print_layout_applied"] is True
    assert rendered["page_size"] == "A4"
    assert rendered["primitive_count"] == len(
        [p for p in pipeline["render_model"]["primitives"] if p["visible"] and p["printable"]]
    )
    assert rendered["clip_count"] == len(pipeline["render_model"]["clip_regions"])
    assert 'transform="translate(' in rendered["svg"]
    assert report["ok"] is True
    assert report["issues"] == []


def test_renderer_parity_reports_modified_artifact_counts():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    rendered = VisualizationSvgSceneRenderer().render(pipeline).to_dict()
    rendered["primitive_count"] -= 1

    report = VisualizationRendererParityValidator().validate(pipeline, rendered).to_dict()

    assert report["ok"] is False
    assert any(item.startswith("renderer_parity_primitive_count_mismatch") for item in report["issues"])
