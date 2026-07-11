from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_render_validation import VisualizationRenderValidationPipeline
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "visualization"


def _pipeline(name: str) -> dict:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return VisualizationScenePipeline().run(payload).to_dict()


@pytest.mark.parametrize(
    "fixture_name",
    [
        "reference_multitrack_linear.json",
        "reference_multitrack_unicode.json",
        "reference_multitrack_overlays.json",
    ],
)
def test_reference_multitrack_scenes_are_export_safe_and_renderer_neutral(fixture_name: str):
    pipeline = _pipeline(fixture_name)
    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
    svg = VisualizationSvgSceneRenderer().render(pipeline)
    pdf = VisualizationPdfRenderModelRenderer().render(pipeline)

    assert report["export_allowed"] is True
    assert report["fatal_count"] == 0
    assert report["error_count"] == 0
    assert svg.export_ready is True
    assert pdf.export_ready is True
    assert svg.geometry_signature == pdf.geometry_signature
    assert svg.primitive_count == pdf.primitive_count
    assert svg.clip_count == pdf.clip_count


def test_svg_and_pdf_exports_are_blocked_by_fatal_layout_error():
    pipeline = deepcopy(_pipeline("reference_multitrack_linear.json"))
    pipeline["print_layout"]["pages"][0]["content_bounds"]["x"] = 0

    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()
    svg = VisualizationSvgSceneRenderer().render(pipeline)
    pdf = VisualizationPdfRenderModelRenderer().render(pipeline)

    assert report["export_allowed"] is False
    assert report["fatal_count"] >= 1
    assert svg.export_ready is False
    assert svg.svg == ""
    assert "svg_renderer_blocked_by_render_validation" in svg.issues
    assert pdf.export_ready is False
    assert pdf.pdf_bytes == b""
    assert "pdf_renderer_blocked_by_render_validation" in pdf.issues


def test_label_collision_is_classified_and_blocks_strict_export():
    pipeline = deepcopy(_pipeline("reference_multitrack_linear.json"))
    labels = [
        item
        for item in pipeline["render_model"]["primitives"]
        if item["kind"] == "text" and item["payload"].get("data_kind") in {"curve_label", "track_title"}
    ]
    labels[1]["payload"]["x"] = labels[0]["payload"]["x"]
    labels[1]["payload"]["y"] = labels[0]["payload"]["y"]

    report = VisualizationRenderValidationPipeline().validate(pipeline).to_dict()

    assert report["export_allowed"] is False
    assert report["error_count"] >= 1
    finding = next(item for item in report["findings"] if "label_overlap" in item["code"])
    assert finding == {"code": finding["code"], "severity": "error", "blocking": True}
