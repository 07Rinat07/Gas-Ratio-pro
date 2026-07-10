from __future__ import annotations

from services.las_manager_service import LasManagerService
from services.las_visualization_payload_service import LasVisualizationPayloadService
from services.visualization_scene_pipeline import VisualizationScenePipeline

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


def test_visualization_scene_pipeline_returns_valid_renderer_neutral_result(tmp_path):
    result = VisualizationScenePipeline().run(_payload(tmp_path)).to_dict()

    assert result["schema"] == "visualization.scene.pipeline.result"
    assert result["stages"] == ["domain_model", "context", "scene", "validation"]
    assert result["ok"] is True
    assert result["domain_model"]["schema"] == "visualization.domain.model"
    assert result["domain_model"]["source_type"] == "las"
    assert result["domain_model"]["raw_dataframe_included"] is False
    assert result["context"]["track_count"] == 3
    assert result["context"]["curve_count"] == 3
    assert result["context"]["overlay_count"] == 1
    assert result["scene"]["schema"] == "visualization.engine.scene"
    assert result["scene"]["render_hints"]["ui_must_not_recalculate"] is True
    assert result["validation"]["renderer_neutral"] is True
    assert result["validation"]["issues"] == []


def test_visualization_scene_pipeline_reports_invalid_empty_payload() -> None:
    result = VisualizationScenePipeline().run({}).to_dict()

    assert result["ok"] is False
    assert "scene_pipeline_input_has_no_tracks" in result["validation"]["issues"]
    assert "scene_pipeline_input_has_no_curves" in result["validation"]["issues"]
    assert "scene_has_no_tracks" in result["validation"]["issues"]
    assert "scene_has_no_layers" in result["validation"]["issues"]
