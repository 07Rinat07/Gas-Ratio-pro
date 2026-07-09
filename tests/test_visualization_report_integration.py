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


def test_bundle_export_manifest_records_visualization_contract(tmp_path) -> None:
    from reports.presentation_export import PresentationExportOptions, export_presentation_bundle_package

    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=False)
    assert payload.presentation_model is not None
    model = replace(payload.presentation_model, visualization_payloads=(_visualization_payload(),))

    result = export_presentation_bundle_package(
        model,
        options=PresentationExportOptions(
            output_dir=tmp_path,
            base_name="visualization-report",
            include_figures=True,
            include_technical_appendix=False,
            overwrite=True,
        ),
    )

    import json

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["figure_count"] == 1
    assert manifest["visualization"]["preview_count"] == 1
    assert manifest["visualization"]["export_ready"] is True
    assert manifest["visualization"]["formats"] == ["svg"]
    assert manifest["visualization"]["contains_raw_dataframe"] is False
    assert manifest["visualization"]["total_tracks"] == 2
    assert manifest["consistency"]["same_visualization_preview_count"] is True


def test_bundle_export_writes_shared_visualization_svg_asset(tmp_path) -> None:
    from reports.presentation_export import PresentationExportOptions, export_presentation_bundle_package, validate_presentation_bundle_export

    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=False)
    assert payload.presentation_model is not None
    model = replace(payload.presentation_model, visualization_payloads=(_visualization_payload(),))

    result = export_presentation_bundle_package(
        model,
        options=PresentationExportOptions(
            output_dir=tmp_path,
            base_name="visualization-report",
            include_figures=True,
            include_technical_appendix=False,
            overwrite=True,
        ),
    )

    import json

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assets = manifest["visualization"]["assets"]
    assert manifest["visualization"]["asset_count"] == 1
    assert manifest["visualization"]["single_shared_asset_source"] is True
    assert manifest["consistency"]["same_visualization_asset_count"] is True
    asset_name = assets["visualization_preview_1"]
    asset_path = tmp_path / asset_name
    assert asset_path.exists()
    assert asset_path.read_text(encoding="utf-8").startswith("<svg")

    validation = validate_presentation_bundle_export(result.manifest_path)
    assert validation.ok is True
    assert asset_path in validation.files_checked


def test_bundle_export_writes_visualization_asset_index_for_external_tools(tmp_path) -> None:
    from reports.presentation_export import PresentationExportOptions, export_presentation_bundle_package, validate_presentation_bundle_export

    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=False)
    assert payload.presentation_model is not None
    model = replace(payload.presentation_model, visualization_payloads=(_visualization_payload(),))

    result = export_presentation_bundle_package(
        model,
        options=PresentationExportOptions(
            output_dir=tmp_path,
            base_name="visualization-report",
            include_figures=True,
            include_technical_appendix=False,
            overwrite=True,
        ),
    )

    import json

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    index_name = manifest["visualization"]["asset_index"]
    index_path = tmp_path / index_name
    assert manifest["files"]["visualization_asset_index"] == index_name
    assert manifest["visualization"]["asset_index_schema"] == "gas-ratio-pro/presentation/visualization-assets/v1"
    assert manifest["consistency"]["visualization_asset_index_ready"] is True

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["schema"] == "gas-ratio-pro/presentation/visualization-assets/v1"
    assert index["asset_count"] == 1
    assert index["all_export_ready"] is True
    assert index["contains_raw_dataframe"] is False
    assert index["assets"][0]["id"] == "visualization_preview_1"
    assert index["assets"][0]["format"] == "svg"
    assert index["assets"][0]["size_bytes"] > 0
    assert len(index["assets"][0]["sha256"]) == 64

    validation = validate_presentation_bundle_export(result.manifest_path)
    assert validation.ok is True
    assert index_path in validation.files_checked
