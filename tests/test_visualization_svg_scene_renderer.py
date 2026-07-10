from __future__ import annotations

from services.las_manager_service import LasManagerService
from services.las_visualization_payload_service import LasVisualizationPayloadService
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer

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


def test_svg_scene_renderer_consumes_pipeline_scene_without_legacy_payload_fields(tmp_path):
    payload = _payload(tmp_path)
    source = payload["scene_pipeline"]
    rendered = VisualizationSvgSceneRenderer().render(source).to_dict()

    assert rendered["schema"] == "visualization.renderer.svg.result"
    assert rendered["source_schema"] == "visualization.scene.pipeline.result"
    assert rendered["export_ready"] is True
    assert rendered["track_count"] == 3
    assert rendered["curve_count"] == 3
    assert rendered["overlay_count"] == 4
    assert rendered["contains_raw_dataframe"] is False
    assert rendered["svg"].startswith("<svg")
    assert 'data-track="track.gamma"' in rendered["svg"]
    assert 'data-kind="curve"' in rendered["svg"]
    assert 'data-kind="interval_overlay"' in rendered["svg"]


def test_las_payload_exposes_svg_renderer_result_from_scene_pipeline(tmp_path):
    payload = _payload(tmp_path)
    rendered = payload["scene_renderers"]["svg"]

    assert rendered["renderer"] == "visualization_svg_scene_renderer"
    assert rendered["export_ready"] is True
    assert rendered["track_count"] == payload["scene_pipeline"]["validation"]["track_count"]
    assert rendered["layer_count"] == payload["scene_pipeline"]["validation"]["layer_count"]
    assert rendered["svg"].startswith("<svg")


def test_svg_scene_renderer_returns_safe_empty_artifact_for_invalid_pipeline():
    pipeline = VisualizationScenePipeline().run({}).to_dict()
    rendered = VisualizationSvgSceneRenderer().render(pipeline).to_dict()

    assert rendered["export_ready"] is False
    assert "svg_renderer_scene_has_no_tracks" in rendered["issues"]
    assert "svg_renderer_scene_has_no_layers" in rendered["issues"]
    assert "svg_renderer_invalid_depth_domain" in rendered["issues"]
    assert "Visualization scene is empty" in rendered["svg"]
