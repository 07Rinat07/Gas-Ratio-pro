from __future__ import annotations

from services.visualization_print_center_contract import VisualizationPrintCenterService
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload() -> dict:
    tracks = []
    curves = []
    for index in range(12):
        track_id = f"track.{index}"
        tracks.append({"id": track_id, "title": f"Track {index + 1}", "width": 1.0})
        curves.append(
            {
                "id": f"curve.{index}",
                "track_id": track_id,
                "mnemonic": f"C{index + 1}",
                "unit": "u",
                "scale_type": "linear",
                "range": {"min": 0, "max": 100},
                "points": [
                    {"depth": 1000.0, "value": float(index + 1)},
                    {"depth": 1001.0, "value": float(index + 2)},
                ],
            }
        )
    return {
        "source_type": "las",
        "source_id": "print-center-contract-test",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1001.0, "step": 1.0},
        "tracks": tracks,
        "curves": curves,
        "overlays": [],
        "print_options": {
            "profile_id": "a4_landscape",
            "page_chrome": {
                "enabled": True,
                "locale": "en",
                "title": "Well A-17",
                "footer_text": "GAS RATIO PRO",
            },
        },
    }


def test_print_center_prepares_one_package_and_exact_profile_summary():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    prepared = VisualizationPrintCenterService().prepare(
        pipeline,
        locale="en",
        title="Well A-17",
        raster_dpi=150,
    )

    assert prepared.export_ready is True
    assert prepared.summary.profile_id == "a4_landscape"
    assert prepared.summary.page_count == 2
    assert prepared.summary.page_count_label == "2 pages"
    assert prepared.summary.exact_profile_label == "A4 · Landscape · 96 DPI · 2 pages"
    assert prepared.summary.page_chrome_enabled is True
    assert prepared.summary.repeated_legend_enabled is True

    output = prepared.output_contract(title="Well A-17")
    assert output["pdf"]["page_count"] == 2
    assert len(output["svg"]["pages"]) == 2
    assert len(output["png"]["pages"]) == 2
    assert output["docx_html_preview"]["page_count"] == 2
    assert output["geometry_signature"] == prepared.package.geometry_signature
    assert output["single_page_fallback"] is False


def test_print_center_summary_is_localized_for_ru_kk_en():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    service = VisualizationPrintCenterService()

    ru = service.prepare(pipeline, locale="ru", raster_dpi=96).summary
    kk = service.prepare(pipeline, locale="kk", raster_dpi=96).summary
    en = service.prepare(pipeline, locale="en", raster_dpi=96).summary

    assert ru.page_count_label == "2 страницы"
    assert "Альбомная" in ru.exact_profile_label
    assert kk.page_count_label == "2 бет"
    assert "Альбомдық" in kk.exact_profile_label
    assert en.page_count_label == "2 pages"
    assert "Landscape" in en.exact_profile_label
