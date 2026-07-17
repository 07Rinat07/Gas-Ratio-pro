from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from services.visualization_page_aware_package import VisualizationPageAwarePackageBuilder
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload(*, locale: str = "ru", track_count: int = 8) -> dict:
    tracks = []
    curves = []
    for index in range(track_count):
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
        "source_id": "page-chrome-test",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1001.0, "step": 1.0},
        "tracks": tracks,
        "curves": curves,
        "overlays": [],
        "print_options": {
            "page_size": "A4",
            "orientation": "portrait",
            "page_chrome": {
                "enabled": True,
                "locale": locale,
                "title": "Well A-17",
                "subtitle": "Composite log",
                "classification": "ENGINEERING USE",
                "document_code": "GRP-A17",
                "footer_text": "GAS RATIO PRO",
                "repeat_legend": True,
            },
        },
    }


def test_page_chrome_is_built_once_in_physical_page_coordinates():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    layout = pipeline["print_layout"]

    assert layout["page_chrome"]["enabled"] is True
    assert layout["metadata"]["page_chrome_enabled"] is True
    assert layout["metadata"]["page_chrome_primitive_count"] > 0
    assert len(layout["pages"]) == 2
    for page in layout["pages"]:
        assert page["header_bounds"] is not None
        assert page["footer_bounds"] is not None
        assert page["chrome_primitives"]
        assert all(item["coordinate_space"] == "page_pt" for item in page["chrome_primitives"])
        assert any(item["id"].endswith("page-number") for item in page["chrome_primitives"])
        assert any("legend" in item["id"] for item in page["chrome_primitives"])


def test_svg_pdf_png_share_localized_page_chrome_and_geometry_signature():
    pipeline = VisualizationScenePipeline().run(_payload(locale="kk")).to_dict()
    package = VisualizationPageAwarePackageBuilder().build(pipeline, raster_dpi=150)

    assert package.export_ready is True
    assert package.page_chrome["locale"] == "kk"
    assert package.page_count == 2
    assert len(PdfReader(BytesIO(package.pdf_bytes)).pages) == 2
    assert all(page.chrome_primitive_count > 0 for page in package.pages)
    assert 'data-coordinate-space="page_pt"' in package.pages[0].svg
    assert "Бет 1 / 2" in package.pages[0].svg
    assert "Шартты белгілер" in package.pages[0].svg
    assert "Бет 2 / 2" in package.pages[1].svg

    preview = package.preview_contract(title="A-17")
    assert preview["page_chrome_enabled"] is True
    assert preview["page_chrome_primitive_counts"] == [page.chrome_primitive_count for page in package.pages]
    assert preview["single_page_fallback"] is False
