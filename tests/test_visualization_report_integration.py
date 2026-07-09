from __future__ import annotations

from dataclasses import replace

import pandas as pd

from reports.document_model import DocumentVisualizationPreview, build_engineering_document
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_html import build_presentation_html_report


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [2148.2, 2149.0, 2155.0, 2156.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь", "Нефтяная залежь"],
            "c1": [0.1, 0.2, 0.15, 0.12],
            "wh": [6.0, 7.0, 25.0, 26.0],
            "bh": [45.0, 44.0, 10.0, 11.0],
            "c1_c2": [80.0, 82.0, 6.0, 6.5],
            "oil_indicator": [0.04, 0.05, 0.2, 0.22],
            "lithology": ["Sandstone", "Sandstone", "Sandstone", "Sandstone"],
        }
    )


def _visualization_payload() -> dict[str, object]:
    return {
        "project_id": "demo",
        "las_id": "well-a",
        "preview": {
            "kind": "svg_preview",
            "format": "svg",
            "export_ready": True,
            "track_count": 2,
            "curve_count": 3,
            "overlay_count": 1,
            "contains_raw_dataframe": False,
            "svg": '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><polyline points="0,0 10,10"/></svg>',
        },
    }


def test_engineering_document_embeds_visualization_preview_without_raw_data() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=False)
    assert payload.presentation_model is not None
    model = replace(payload.presentation_model, visualization_payloads=(_visualization_payload(),))

    document = build_engineering_document(model, include_figures=True)

    preview_blocks = [
        block
        for section in document.sections
        for block in section.blocks
        if isinstance(block, DocumentVisualizationPreview)
    ]
    assert document.visualization_preview_count == 1
    assert len(preview_blocks) == 1
    assert preview_blocks[0].preview["contains_raw_dataframe"] is False


def test_html_report_renders_visualization_svg_preview_from_document_model() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=False)
    assert payload.presentation_model is not None
    model = replace(payload.presentation_model, visualization_payloads=(_visualization_payload(),))

    rendered = build_presentation_html_report(model)
    html = rendered.content.decode("utf-8")

    assert rendered.figure_count == 1
    assert "LAS visualization preview" in html
    assert "<svg" in html
    assert "Tracks: 2" in html
    assert "dataframe" not in html.lower()
