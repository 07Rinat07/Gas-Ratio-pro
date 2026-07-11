from __future__ import annotations

from dataclasses import replace

from services.visualization_export_qa import VisualizationExportQaValidator
from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


def _payload():
    return {
        "source_type": "las",
        "source_id": "export-qa-demo",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1002.0, "step": 1.0},
        "tracks": [{"id": "track.gamma", "title": "Гамма-каротаж", "width": 1.0}],
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
        "overlays": [{
            "id": "interval.1",
            "top": 1000.5,
            "base": 1001.5,
            "label": "Газовый интервал",
            "fluid_type": "gas",
            "track_scope": ["track.gamma"],
        }],
    }


def _artifacts():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    svg = VisualizationSvgSceneRenderer().render(pipeline)
    pdf = VisualizationPdfRenderModelRenderer().render(pipeline)
    return pipeline, svg, pdf


def test_export_qa_accepts_matching_svg_and_pdf_artifacts():
    pipeline, svg, pdf = _artifacts()
    report = VisualizationExportQaValidator().validate(pipeline, svg, pdf).to_dict()

    assert report["ok"] is True
    assert report["svg_ok"] is True
    assert report["pdf_ok"] is True
    assert report["renderer_parity_ok"] is True
    assert report["geometry_signature_match"] is True
    assert report["expected_primitive_count"] == report["svg_primitive_count"]
    assert report["expected_clip_count"] == report["svg_clip_count"]
    assert report["pdf_page_count"] == 1
    assert report["page_width_pt"] > 0
    assert report["page_height_pt"] > 0
    assert report["issues"] == []


def test_export_qa_rejects_invalid_svg_xml():
    pipeline, svg, pdf = _artifacts()
    broken_svg = replace(svg, svg="<svg>")

    report = VisualizationExportQaValidator().validate(pipeline, broken_svg, pdf).to_dict()

    assert report["ok"] is False
    assert report["svg_ok"] is False
    assert "export_qa_svg_invalid_xml" in report["issues"]


def test_export_qa_rejects_pdf_with_invalid_header():
    pipeline, svg, pdf = _artifacts()
    broken_pdf = replace(pdf, pdf_bytes=b"not-a-pdf")

    report = VisualizationExportQaValidator().validate(pipeline, svg, broken_pdf).to_dict()

    assert report["ok"] is False
    assert report["pdf_ok"] is False
    assert "export_qa_pdf_missing_or_invalid_header" in report["issues"]


def test_export_qa_detects_cross_renderer_geometry_mismatch():
    pipeline, svg, pdf = _artifacts()
    broken_pdf = replace(pdf, geometry_signature="0" * 64)

    report = VisualizationExportQaValidator().validate(pipeline, svg, broken_pdf).to_dict()

    assert report["ok"] is False
    assert report["geometry_signature_match"] is False
    assert "export_qa_renderer_geometry_signature_mismatch" in report["issues"]


def test_export_qa_detects_missing_unicode_pdf_font():
    pipeline, svg, pdf = _artifacts()
    broken_pdf = replace(pdf, font_name="")

    report = VisualizationExportQaValidator().validate(pipeline, svg, broken_pdf).to_dict()

    assert report["ok"] is False
    assert report["pdf_ok"] is False
    assert "export_qa_pdf_unicode_font_missing" in report["issues"]
