from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from services.visualization_page_aware_package import VisualizationPageAwarePackageBuilder
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload(track_count: int = 12, *, page_size: str = "A4", orientation: str = "landscape") -> dict:
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
        "source_id": "page-aware-package-test",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1001.0, "step": 1.0},
        "tracks": tracks,
        "curves": curves,
        "overlays": [],
        "print_options": {"page_size": page_size, "orientation": orientation},
    }


def test_page_aware_package_unifies_svg_png_pdf_and_preview_contract():
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    package = VisualizationPageAwarePackageBuilder().build(pipeline, raster_dpi=150)

    assert package.export_ready is True
    assert package.profile_id == "a4_landscape"
    assert package.page_count == len(pipeline["print_layout"]["pages"]) == 2
    assert len(PdfReader(BytesIO(package.pdf_bytes)).pages) == package.page_count
    assert [track for page in package.pages for track in page.track_ids] == [f"track.{i}" for i in range(12)]
    assert all(page.svg.startswith("<svg") for page in package.pages)
    assert all(page.png_bytes.startswith(b"\x89PNG\r\n\x1a\n") for page in package.pages)

    preview = package.preview_contract(title="Well A")
    assert preview["schema"] == "visualization.preview.page-aware"
    assert preview["page_count"] == 2
    assert preview["page_svgs"] == [page.svg for page in package.pages]
    assert preview["single_page_fallback"] is False
    assert preview["geometry_signature"] == package.geometry_signature


def test_page_aware_package_rejects_non_pipeline_input_without_fallback():
    package = VisualizationPageAwarePackageBuilder().build({})

    assert package.export_ready is False
    assert package.page_count == 0
    assert package.issues == ("page_aware_package_unsupported_pipeline_schema",)
    assert package.to_dict()["single_page_fallback"] is False
