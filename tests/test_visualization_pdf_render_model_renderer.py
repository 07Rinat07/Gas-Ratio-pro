from __future__ import annotations

from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_renderer_parity import VisualizationRendererParityValidator
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload():
    return {
        "source_type": "las",
        "source_id": "pdf-parity-demo",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1002.0, "step": 1.0},
        "tracks": [{"id": "track.gamma", "title": "Гамма", "width": 1.0}],
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
                    {"depth": 1002.0, "value": 72.0},
                ],
            }
        ],
        "overlays": [
            {
                "id": "interval.1",
                "top": 1000.5,
                "base": 1001.5,
                "label": "Газовый интервал",
                "fluid_type": "gas",
                "track_scope": ["track.gamma"],
            }
        ],
    }


def test_pdf_renderer_consumes_render_model_and_applies_print_layout():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    result = VisualizationPdfRenderModelRenderer().render(pipeline)
    metadata = result.to_dict()

    assert result.pdf_bytes.startswith(b"%PDF-")
    assert metadata["schema"] == "visualization.renderer.pdf.result"
    assert metadata["source_schema"] == "visualization.scene.pipeline.result"
    assert metadata["export_ready"] is True
    assert metadata["print_layout_applied"] is True
    assert metadata["page_size"] == "A4"
    assert metadata["page_count"] == 1
    assert metadata["byte_size"] > 500
    assert len(metadata["sha256"]) == 64
    assert metadata["primitive_count"] == len(
        [item for item in pipeline["render_model"]["primitives"] if item["visible"] and item["printable"]]
    )
    assert metadata["clip_count"] == len(pipeline["render_model"]["clip_regions"])


def test_pdf_renderer_passes_shared_renderer_parity_validation():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    metadata = VisualizationPdfRenderModelRenderer().render(pipeline).to_dict()
    report = VisualizationRendererParityValidator().validate(pipeline, metadata).to_dict()

    assert report["renderer"] == "visualization_pdf_render_model_renderer"
    assert report["ok"] is True
    assert report["issues"] == []


def test_pdf_renderer_returns_safe_result_for_invalid_source():
    result = VisualizationPdfRenderModelRenderer().render({}).to_dict()

    assert result["export_ready"] is False
    assert "pdf_renderer_unsupported_source_schema" in result["issues"]
    assert "pdf_renderer_render_model_missing" in result["issues"]
    assert "pdf_renderer_no_printable_primitives" in result["issues"]
