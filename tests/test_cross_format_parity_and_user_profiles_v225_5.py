from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from core.physical_print_profiles import (
    UserPhysicalPrintProfileStore,
    build_user_physical_print_profile,
)
from services.page_aware_static_export import build_page_aware_static_artifact
from services.visualization_page_aware_package import VisualizationPageAwarePackageBuilder
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload(track_count: int = 8, *, profile: dict | None = None) -> dict:
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
    print_options = {
        "page_size": "A4",
        "orientation": "landscape",
        "page_chrome": {"enabled": True, "locale": "ru", "repeat_legend": True},
    }
    if profile is not None:
        print_options.update({"profile_id": profile["id"], "physical_profile": profile})
    return {
        "source_type": "las",
        "source_id": "v225.5-test",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1001.0, "step": 1.0},
        "tracks": tracks,
        "curves": curves,
        "overlays": [],
        "print_options": print_options,
    }


def test_user_profile_store_round_trip_and_safety_floor(tmp_path):
    profile = build_user_physical_print_profile(
        name="Client A4",
        page_size="A4",
        orientation="landscape",
        margin_mm=18,
        dpi=300,
        minimum_font_pt=2,
        minimum_line_width_pt=0.1,
        minimum_track_width_mm=5,
        max_tracks_per_page=99,
    )
    assert profile.id == "user_client-a4"
    assert profile.minimum_font_pt == 7.5
    assert profile.minimum_line_width_pt == 0.5
    assert profile.minimum_track_width_mm == 28.0
    assert profile.max_tracks_per_page == 6

    store = UserPhysicalPrintProfileStore(tmp_path / "profiles.json")
    store.upsert(profile)
    assert store.resolve(profile.id) == profile
    assert store.delete(profile.id) is True
    assert store.load() == ()


def test_user_profile_controls_layout_and_is_reported_in_metadata():
    profile = build_user_physical_print_profile(
        name="A3 QA",
        page_size="A3",
        orientation="portrait",
        margin_mm=20,
        dpi=300,
        minimum_font_pt=9,
        minimum_track_width_mm=35,
        max_tracks_per_page=4,
    )
    pipeline = VisualizationScenePipeline().run(_payload(8, profile=profile.to_dict())).to_dict()
    layout = pipeline["print_layout"]
    assert layout["profile_id"] == profile.id
    assert layout["page_size"] == "A3"
    assert layout["orientation"] == "portrait"
    assert layout["margin_mm"] == 20
    assert layout["dpi"] == 300
    assert layout["metadata"]["user_profile_applied"] is True
    assert all(1 <= len(page["track_ids"]) <= 4 for page in layout["pages"])
    assert sum(len(page["track_ids"]) for page in layout["pages"]) == 8


def test_cross_format_parity_gate_is_blocking_and_passes_for_valid_package():
    pipeline = VisualizationScenePipeline().run(_payload(8)).to_dict()
    package = VisualizationPageAwarePackageBuilder().build(pipeline, raster_dpi=150)
    assert package.export_ready is True
    assert package.parity_gate["ok"] is True
    assert package.parity_gate["format_page_counts"]["svg"] == package.page_count
    assert package.parity_gate["format_page_counts"]["docx_preview"] == package.page_count
    assert package.preview_contract()["cross_format_parity_passed"] is True


def test_multi_page_svg_png_delivery_is_zip_not_first_page_fallback():
    pipeline = VisualizationScenePipeline().run(_payload(8)).to_dict()
    package = VisualizationPageAwarePackageBuilder().build(pipeline, raster_dpi=150)
    assert package.page_count == 2

    for format_name in ("svg", "png"):
        artifact = build_page_aware_static_artifact(package, format_name=format_name, base_name="well-a")
        assert artifact.bundled is True
        assert artifact.mime_type == "application/zip"
        with ZipFile(BytesIO(artifact.content)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["page_count"] == 2
            assert manifest["single_page_fallback"] is False
            assert len(manifest["files"]) == 2
            assert all(name in archive.namelist() for name in manifest["files"])


def test_static_delivery_rejects_unready_package():
    package = VisualizationPageAwarePackageBuilder().build({})
    with pytest.raises(ValueError, match="package_not_ready"):
        build_page_aware_static_artifact(package, format_name="svg", base_name="invalid")
