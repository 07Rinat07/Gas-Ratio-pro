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
        }
    ]
    assert "dataframe" not in payload


def test_las_visualization_payload_reports_empty_overlay_flag_for_invalid_intervals(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record

    payload = LasVisualizationPayloadService(tmp_path).build("demo", record.id, interval_ids=["bad_interval"]).to_dict()

    assert payload["overlays"] == []
    assert "interval_overlays_empty" in payload["quality_flags"]
