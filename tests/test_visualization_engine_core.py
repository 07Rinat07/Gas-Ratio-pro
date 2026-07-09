from __future__ import annotations

from services.las_manager_service import LasManagerService
from services.las_visualization_payload_service import LasVisualizationPayloadService
from services.visualization_engine_core import VisualizationEngineCore

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


def _payload(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(project_id="demo", data=LAS_WITH_GAS, file_name="demo.las").record
    return LasVisualizationPayloadService(tmp_path).build(
        "demo",
        record.id,
        interval_ids=["1000.5-1001.0"],
        interval_metadata={"1000.5-1001.0": {"fluid_type": "gas", "label": "Gas interval"}},
    ).to_dict()


def test_visualization_engine_core_builds_scene_with_layers_and_depth_sync(tmp_path):
    payload = _payload(tmp_path)
    scene = VisualizationEngineCore().build_scene(payload).to_dict()

    assert scene["schema"] == "visualization.engine.scene"
    assert scene["version"] == "1.0"
    assert scene["depth_sync"] == {
        "mode": "shared_depth_axis",
        "depth_curve": "DEPT",
        "unit": "M",
        "start": 1000.0,
        "stop": 1001.5,
        "step": 0.5,
        "track_ids": ["track.gamma", "track.gas", "track.porosity"],
        "inverted": True,
    }
    assert [track["id"] for track in scene["tracks"]] == ["track.gamma", "track.gas", "track.porosity"]
    layer_kinds = [layer["kind"] for layer in scene["layers"]]
    assert layer_kinds.count("curve") == 3
    assert layer_kinds.count("interval_overlay") == 4
    assert scene["quality"]["raw_dataframe_included"] is False


def test_las_visualization_payload_exposes_engine_scene_contract(tmp_path):
    payload = _payload(tmp_path)
    scene = payload["engine_scene"]

    assert scene["schema"] == "visualization.engine.scene"
    assert scene["render_hints"]["renderer_neutral"] is True
    assert scene["render_hints"]["ui_must_not_recalculate"] is True
    assert scene["render_hints"]["visible_tracks"] == ["track.gamma", "track.gas", "track.porosity"]
    assert scene["quality"]["curve_layer_count"] == 3
    assert scene["quality"]["overlay_layer_count"] == 4
    assert "dataframe" not in scene
