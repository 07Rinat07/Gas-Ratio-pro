from __future__ import annotations

from services.las_manager_service import LasManagerService
from services.las_visualization_payload_service import LasVisualizationPayloadService

LAS_WITH_GAS = b"""~Version Information
VERS. 2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0
WRAP. NO : ONE LINE PER DEPTH STEP
~Well Information
STRT.M 1000.0 : START DEPTH
STOP.M 1001.5 : STOP DEPTH
STEP.M 0.5 : STEP
NULL. -999.25 : NULL VALUE
WELL. Demo : WELL
~Curve Information
DEPT.M : DEPTH
GR.API : Gamma Ray
C1.PPM : Methane
RHOB.G/C3 : Bulk Density
~ASCII
1000.0 80 12 2.31
1000.5 82 18 2.33
1001.0 85 25 2.36
1001.5 90 30 2.40
"""


def test_las_visualization_payload_is_renderer_neutral_and_sampled(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(
        project_id="demo",
        data=LAS_WITH_GAS,
        file_name="demo.las",
        well_name="Demo Well",
    ).record

    payload = LasVisualizationPayloadService(tmp_path).build("demo", record.id, sample_limit=3).to_dict()

    assert payload["project_id"] == "demo"
    assert payload["las_id"] == record.id
    assert payload["depth_curve"] == "DEPT"
    assert payload["depth_unit"] == "M"
    assert payload["depth_range"] == {"start": 1000.0, "stop": 1001.5, "step": 0.5}
    assert [track["id"] for track in payload["tracks"]] == ["track.gamma", "track.gas", "track.porosity"]
    gr_curve = next(curve for curve in payload["curves"] if curve["mnemonic"] == "GR")
    assert gr_curve["track_id"] == "track.gamma"
    assert gr_curve["point_count"] == 4
    assert gr_curve["sampled_count"] == 3
    assert gr_curve["points"][0] == {"depth": 1000.0, "value": 80.0}
    assert "curves_decimated" in payload["quality_flags"]


def test_las_visualization_payload_limits_curves_without_raw_dataframe(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build("demo", record.id, curve_limit=1).to_dict()

    assert len(payload["curves"]) == 1
    assert payload["curves"][0]["mnemonic"] == "GR"
    assert "curves_truncated" in payload["quality_flags"]
    assert "dataframe" not in payload


def test_las_visualization_payload_adds_renderer_neutral_interval_overlays(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build(
        "demo",
        record.id,
        interval_ids=["1000.5-1001.0", "outside"],
        interval_metadata={
            "1000.5-1001.0": {
                "label": "Gas bearing interval",
                "fluid_type": "gas",
                "confidence": "high",
            }
        },
    ).to_dict()

    assert payload["overlays"] == [
        {
            "id": "1000.5-1001.0",
            "top": 1000.5,
            "base": 1001.0,
            "label": "Gas bearing interval",
            "fluid_type": "gas",
            "confidence": "high",
            "selected": True,
            "track_scope": ["track.gamma", "track.gas", "track.resistivity", "track.porosity"],
            "style": {"palette_key": "fluid.gas", "fill": "#ef8f35", "stroke": "#a84c00"},
        }
    ]
    assert "dataframe" not in payload


def test_las_visualization_payload_reports_empty_overlay_flag_for_invalid_intervals(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build("demo", record.id, interval_ids=["bad_interval"]).to_dict()

    assert payload["overlays"] == []
    assert "interval_overlays_empty" in payload["quality_flags"]


def test_las_visualization_payload_exposes_axis_style_and_print_profile(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build("demo", record.id).to_dict()

    gamma_track = next(track for track in payload["tracks"] if track["id"] == "track.gamma")
    gamma_curve = next(curve for curve in payload["curves"] if curve["mnemonic"] == "GR")

    assert gamma_track["style"]["palette_key"] == "gamma"
    assert gamma_track["axis"] == {"depth_unit": "", "orientation": "vertical", "grid": True}
    assert gamma_curve["axis"]["unit"] == "API"
    assert gamma_curve["axis"]["scale"] == "linear"
    assert gamma_curve["style"]["stroke"] == "#2f7d32"
    assert payload["print_profile"] == {
        "quality": "print",
        "preferred_format": "svg_pdf",
        "depth_axis": "vertical",
        "min_curve_width_px": 2,
        "grid": True,
        "legend": True,
    }

LAS_WITH_GAPS_AND_NULLS = b"""~Version Information
VERS. 2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0
WRAP. NO : ONE LINE PER DEPTH STEP
~Well Information
STRT.M 1000.0 : START DEPTH
STOP.M 1008.0 : STOP DEPTH
STEP.M 0.5 : STEP
NULL. -999.25 : NULL VALUE
WELL. Demo : WELL
~Curve Information
DEPT.M : DEPTH
GR.API : Gamma Ray
C1.PPM : Methane
~ASCII
1000.0 80 12
1000.5 -999.25 18
1001.0 85 25
1008.0 90 30
"""


def test_las_visualization_payload_exposes_sampling_and_quality_metadata(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAPS_AND_NULLS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build("demo", record.id, sample_limit=3).to_dict()

    assert payload["sampling_profile"] == {
        "strategy": "depth_preserving_even_decimation",
        "sample_limit": 3,
        "preserve_first_last": True,
        "renderer_may_smooth": True,
        "raw_dataframe_included": False,
    }
    assert payload["data_quality"]["row_count"] == 4
    assert payload["data_quality"]["raw_dataframe_included"] is False
    assert "GR" in payload["data_quality"]["curves_with_depth_gaps"]

    gr_curve = next(curve for curve in payload["curves"] if curve["mnemonic"] == "GR")
    assert gr_curve["sampling"]["strategy"] == "depth_preserving_even_decimation"
    assert gr_curve["sampling"]["preserve_first_last"] is True
    assert gr_curve["quality"]["missing_points"] == 1
    assert gr_curve["quality"]["has_depth_gaps"] is True
    assert gr_curve["quality"]["depth_gaps"] == [7.0]


def test_las_visualization_payload_exposes_renderer_ready_legend_and_summary(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build(
        "demo",
        record.id,
        interval_ids=["1000.5-1001.0"],
        interval_metadata={"1000.5-1001.0": {"fluid_type": "gas", "label": "Gas bearing interval"}},
    ).to_dict()

    assert payload["visible_tracks"] == ["track.gamma", "track.gas", "track.porosity"]
    assert payload["plot_summary"] == {
        "title": "LAS visualization",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_start": 1000.0,
        "depth_stop": 1001.5,
        "track_count": 3,
        "curve_count": 3,
        "overlay_count": 1,
        "renderer_ready": True,
    }
    legend_ids = [item["id"] for item in payload["legend"]]
    assert legend_ids == ["curve.GR", "curve.C1", "curve.RHOB", "overlay.gas"]
    assert payload["legend"][0]["label"] == "GR (API)"
    assert payload["legend"][-1]["label"] == "Gas interval"


def test_las_visualization_payload_exposes_lightweight_svg_preview(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build(
        "demo",
        record.id,
        interval_ids=["1000.5-1001.0"],
        interval_metadata={"1000.5-1001.0": {"fluid_type": "gas", "label": "Gas interval"}},
    ).to_dict()

    preview = payload["preview"]
    assert preview["kind"] == "svg_preview"
    assert preview["format"] == "svg"
    assert preview["export_ready"] is True
    assert preview["contains_raw_dataframe"] is False
    assert preview["track_count"] == 3
    assert preview["curve_count"] == 3
    assert preview["overlay_count"] == 1
    assert preview["svg"].startswith("<svg")
    assert "data-track=&quot;track.gamma&quot;" not in preview["svg"]
    assert 'data-track="track.gamma"' in preview["svg"]
    assert "<polyline" in preview["svg"]


def test_las_visualization_payload_exposes_scene_pipeline_contract(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build("demo", record.id).to_dict()

    assert payload["scene_pipeline"]["schema"] == "visualization.scene.pipeline.result"
    assert payload["scene_pipeline"]["ok"] is True
    assert payload["scene_pipeline"]["context"]["curve_count"] == 3
    assert payload["scene_pipeline"]["scene"] == payload["engine_scene"]
    assert payload["scene_pipeline"]["validation"]["renderer_neutral"] is True
