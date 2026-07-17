from __future__ import annotations

from io import BytesIO
import re

from pypdf import PdfReader

from core.physical_print_profiles import resolve_physical_print_profile
from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_png_scene_renderer import VisualizationPngSceneRenderer
from services.visualization_export_qa import VisualizationExportQaValidator
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


def _wide_payload(*, track_count: int, page_size: str, orientation: str) -> dict:
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
        "source_id": "physical-print-profile-test",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1001.0, "step": 1.0},
        "tracks": tracks,
        "curves": curves,
        "overlays": [],
        "print_options": {"page_size": page_size, "orientation": orientation},
    }


def test_a4_a3_profiles_define_distinct_portrait_and_landscape_limits():
    profiles = {
        profile.id: profile
        for profile in (
            resolve_physical_print_profile("A4", "portrait"),
            resolve_physical_print_profile("A4", "landscape"),
            resolve_physical_print_profile("A3", "portrait"),
            resolve_physical_print_profile("A3", "landscape"),
        )
    }

    assert set(profiles) == {"a4_portrait", "a4_landscape", "a3_portrait", "a3_landscape"}
    assert profiles["a4_landscape"].max_tracks_per_page > profiles["a4_portrait"].max_tracks_per_page
    assert profiles["a3_landscape"].max_tracks_per_page > profiles["a3_portrait"].max_tracks_per_page
    assert profiles["a3_portrait"].minimum_font_pt >= profiles["a4_portrait"].minimum_font_pt
    assert all(item.minimum_track_width_mm > 0 for item in profiles.values())


def test_a4_landscape_paginates_tracks_without_changing_order_or_coverage():
    pipeline = VisualizationScenePipeline().run(
        _wide_payload(track_count=12, page_size="A4", orientation="landscape")
    ).to_dict()
    print_layout = pipeline["print_layout"]
    pages = print_layout["pages"]

    assert pipeline["validation"]["render_validation_ok"] is True
    assert print_layout["version"] == "2.1"
    assert print_layout["profile_id"] == "a4_landscape"
    assert len(pages) == 2
    assert [track_id for page in pages for track_id in page["track_ids"]] == [
        f"track.{index}" for index in range(12)
    ]
    assert all(len(page["track_ids"]) <= print_layout["max_tracks_per_page"] for page in pages)
    assert pages[1]["source_bounds"]["x"] > pages[0]["source_bounds"]["x"]


def test_a4_portrait_and_a3_landscape_apply_their_own_page_capacity():
    a4 = VisualizationScenePipeline().run(
        _wide_payload(track_count=8, page_size="A4", orientation="portrait")
    ).to_dict()["print_layout"]
    a3 = VisualizationScenePipeline().run(
        _wide_payload(track_count=12, page_size="A3", orientation="landscape")
    ).to_dict()["print_layout"]

    assert a4["profile_id"] == "a4_portrait"
    assert [len(page["track_ids"]) for page in a4["pages"]] == [4, 4]
    assert a3["profile_id"] == "a3_landscape"
    assert [len(page["track_ids"]) for page in a3["pages"]] == [9, 3]


def test_svg_pages_preserve_track_partition_and_physical_type_floor():
    pipeline = VisualizationScenePipeline().run(
        _wide_payload(track_count=12, page_size="A4", orientation="landscape")
    ).to_dict()
    rendered = VisualizationSvgSceneRenderer().render(pipeline).to_dict()

    assert rendered["export_ready"] is True
    assert rendered["page_count"] == len(pipeline["print_layout"]["pages"]) == 2
    assert len(rendered["page_svgs"]) == 2
    assert 'data-track="track.0"' in rendered["page_svgs"][0]
    assert 'data-track="track.6"' not in rendered["page_svgs"][0]
    assert 'data-track="track.6"' in rendered["page_svgs"][1]
    assert 'data-kind="depth_label"' in rendered["page_svgs"][1]

    first_page = pipeline["print_layout"]["pages"][0]
    physical_scale = 72.0 / pipeline["print_layout"]["dpi"] * first_page["content_scale"]
    font_sizes = [float(value) for value in re.findall(r'font-size="([0-9.]+)"', rendered["page_svgs"][0])]
    assert font_sizes
    assert min(font_sizes) * physical_scale >= pipeline["print_layout"]["minimum_font_pt"] - 1e-5
    assert 'vector-effect="non-scaling-stroke"' in rendered["page_svgs"][0]


def test_pdf_page_count_matches_shared_print_layout():
    pipeline = VisualizationScenePipeline().run(
        _wide_payload(track_count=12, page_size="A4", orientation="landscape")
    ).to_dict()
    rendered = VisualizationPdfRenderModelRenderer().render(pipeline)

    assert rendered.export_ready is True
    assert rendered.page_count == len(pipeline["print_layout"]["pages"]) == 2
    assert len(PdfReader(BytesIO(rendered.pdf_bytes)).pages) == 2


def test_png_pages_are_rasterized_from_the_same_physical_svg_partition():
    pipeline = VisualizationScenePipeline().run(
        _wide_payload(track_count=12, page_size="A4", orientation="landscape")
    ).to_dict()
    svg = VisualizationSvgSceneRenderer().render(pipeline)
    png = VisualizationPngSceneRenderer().render(pipeline, dpi=150)

    assert png.export_ready is True
    assert png.page_count == svg.page_count == len(pipeline["print_layout"]["pages"]) == 2
    assert len(png.page_pngs) == 2
    assert all(item.startswith(b"\x89PNG\r\n\x1a\n") for item in png.page_pngs)
    assert png.geometry_signature == svg.geometry_signature
    assert png.width_px > png.height_px


def test_multi_page_svg_and_pdf_pass_aggregate_export_qa():
    pipeline = VisualizationScenePipeline().run(
        _wide_payload(track_count=12, page_size="A4", orientation="landscape")
    ).to_dict()
    svg = VisualizationSvgSceneRenderer().render(pipeline)
    pdf = VisualizationPdfRenderModelRenderer().render(pipeline)
    report = VisualizationExportQaValidator().validate(pipeline, svg, pdf).to_dict()

    assert report["ok"] is True
    assert report["svg_primitive_count"] == report["expected_primitive_count"]
    assert report["svg_clip_count"] == report["expected_clip_count"]
    assert report["pdf_page_count"] == 2
