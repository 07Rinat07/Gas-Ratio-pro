from __future__ import annotations

from services.visualization_interactive_viewport import InteractiveViewport, ViewportLimits
from services.visualization_viewport_pipeline import VisualizationViewportPipeline


def _payload() -> dict:
    return {
        "project_id": "demo",
        "las_id": "well-1",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1010.0, "step": 1.0},
        "tracks": [
            {
                "id": "track.gamma",
                "title": "Gamma Ray",
                "curve_ids": ["GR"],
                "width": 1.0,
                "printable": True,
                "axis": {"orientation": "vertical", "grid": True},
                "style": {"stroke": "#2f7d32"},
            }
        ],
        "curves": [
            {
                "mnemonic": "GR",
                "unit": "API",
                "track_id": "track.gamma",
                "axis": {"scale": "linear", "min": 0.0, "max": 100.0},
                "style": {"stroke": "#2f7d32", "line_width": 1.3},
                "point_count": 6,
                "sampled_count": 6,
                "points": [
                    {"depth": 1000.0, "value": 10.0},
                    {"depth": 1002.0, "value": 20.0},
                    {"depth": 1004.0, "value": 40.0},
                    {"depth": 1006.0, "value": 60.0},
                    {"depth": 1008.0, "value": 80.0},
                    {"depth": 1010.0, "value": 90.0},
                ],
                "quality": {},
            }
        ],
        "overlays": [
            {"id": "a", "track_id": "track.gamma", "top": 1001.0, "base": 1005.0, "label": "A"},
            {"id": "b", "track_id": "track.gamma", "top": 1008.0, "base": 1009.0, "label": "B"},
        ],
    }


def _viewport(start=1003.0, stop=1007.0) -> InteractiveViewport:
    return InteractiveViewport(
        domain_start=start,
        domain_stop=stop,
        screen_start=60.0,
        screen_stop=660.0,
        inverted=True,
        unit="M",
        limits=ViewportLimits(minimum=1000.0, maximum=1010.0),
    )


def test_prepare_payload_filters_points_and_interpolates_boundaries() -> None:
    prepared, profile = VisualizationViewportPipeline().prepare_payload(_payload(), _viewport())

    assert prepared["depth_range"]["start"] == 1003.0
    assert prepared["depth_range"]["stop"] == 1007.0
    points = prepared["curves"][0]["points"]
    assert [point["depth"] for point in points] == [1003.0, 1004.0, 1006.0, 1007.0]
    assert points[0]["value"] == 30.0
    assert points[-1]["value"] == 70.0
    assert points[0]["viewport_interpolated"] is True
    assert profile.source_point_count == 6
    assert profile.visible_point_count == 4


def test_prepare_payload_clips_and_removes_overlays() -> None:
    prepared, profile = VisualizationViewportPipeline().prepare_payload(_payload(), _viewport())

    assert len(prepared["overlays"]) == 1
    assert prepared["overlays"][0]["top"] == 1003.0
    assert prepared["overlays"][0]["base"] == 1005.0
    assert prepared["overlays"][0]["viewport_clipped"] is True
    assert profile.clipped_overlay_count == 1


def test_prepare_payload_does_not_mutate_source() -> None:
    source = _payload()
    VisualizationViewportPipeline().prepare_payload(source, _viewport())

    assert source["depth_range"] == {"start": 1000.0, "stop": 1010.0, "step": 1.0}
    assert len(source["curves"][0]["points"]) == 6
    assert len(source["overlays"]) == 2


def test_viewport_is_clamped_to_source_domain() -> None:
    prepared, profile = VisualizationViewportPipeline().prepare_payload(
        _payload(), _viewport(995.0, 1005.0)
    )

    assert prepared["depth_range"]["start"] == 1000.0
    assert prepared["depth_range"]["stop"] == 1005.0
    assert profile.applied_start == 1000.0
    assert profile.applied_stop == 1005.0


def test_no_intersection_falls_back_with_diagnostic() -> None:
    viewport = InteractiveViewport(
        domain_start=1100.0,
        domain_stop=1110.0,
        screen_start=0.0,
        screen_stop=100.0,
    )
    prepared, profile = VisualizationViewportPipeline().prepare_payload(_payload(), viewport)

    assert prepared["depth_range"]["start"] == 1000.0
    assert prepared["depth_range"]["stop"] == 1010.0
    assert "viewport_pipeline_error:no_domain_intersection" in profile.diagnostics


def test_pipeline_builds_render_model_for_visible_depth_range() -> None:
    result = VisualizationViewportPipeline().run(_payload(), _viewport())

    assert result.ok is True
    assert result.pipeline.render_model.ok is True
    scene = result.pipeline.scene.to_dict()
    assert scene["depth_sync"]["start"] == 1003.0
    assert scene["depth_sync"]["stop"] == 1007.0
    curve_primitives = [
        item for item in result.pipeline.render_model.primitives if item.kind == "polyline"
    ]
    assert curve_primitives
    assert result.profile.visible_point_count == 4


def test_result_contract_is_renderer_neutral() -> None:
    result = VisualizationViewportPipeline().run(_payload(), _viewport()).to_dict()

    assert result["schema"] == "visualization.viewport.pipeline.result"
    assert result["renderer_neutral"] is True
    assert result["profile"]["schema"] == "visualization.viewport.pipeline.profile"
    assert result["profile"]["clipped"] is True
    assert result["payload"]["viewport"]["schema"] == "visualization.interactive.viewport"


def test_repeated_viewport_run_reuses_prepared_payload_and_render_model() -> None:
    pipeline = VisualizationViewportPipeline()

    first = pipeline.run(_payload(), _viewport())
    second = pipeline.run(_payload(), _viewport())

    assert first.profile.cache_hit is False
    assert second.profile.cache_hit is True
    assert second.pipeline.performance.cache_hit is True
    assert second.pipeline.validation["viewport_cache_hit"] is True
    assert second.profile.cache_key == first.profile.cache_key


def test_viewport_cache_key_changes_with_domain() -> None:
    pipeline = VisualizationViewportPipeline()

    first = pipeline.run(_payload(), _viewport(1002.0, 1006.0))
    second = pipeline.run(_payload(), _viewport(1003.0, 1007.0))

    assert first.profile.cache_key != second.profile.cache_key
    assert second.profile.cache_hit is False


def test_viewport_cache_can_be_disabled() -> None:
    payload = _payload()
    payload["viewport_cache"] = False
    pipeline = VisualizationViewportPipeline()

    first = pipeline.run(payload, _viewport())
    second = pipeline.run(payload, _viewport())

    assert first.profile.cache_enabled is False
    assert second.profile.cache_enabled is False
    assert second.profile.cache_hit is False
    assert second.pipeline.validation["viewport_cache_enabled"] is False


def test_viewport_cache_returns_isolated_payload_copy() -> None:
    pipeline = VisualizationViewportPipeline()
    first = pipeline.run(_payload(), _viewport())
    first.payload["curves"][0]["points"].clear()

    second = pipeline.run(_payload(), _viewport())

    assert second.profile.cache_hit is True
    assert len(second.payload["curves"][0]["points"]) == 4


def test_source_change_creates_new_cache_entry() -> None:
    pipeline = VisualizationViewportPipeline()
    source = _payload()

    first = pipeline.run(source, _viewport())
    changed = _payload()
    changed["curves"][0]["points"][2]["value"] = 41.0
    second = pipeline.run(changed, _viewport())

    assert first.profile.cache_key != second.profile.cache_key
    assert second.profile.cache_hit is False
    assert second.payload["viewport_pipeline"]["source_fingerprint"] != first.payload["viewport_pipeline"]["source_fingerprint"]


def test_render_configuration_change_creates_new_cache_entry() -> None:
    pipeline = VisualizationViewportPipeline()
    first = pipeline.run(_payload(), _viewport())
    changed = _payload()
    changed["tracks"][0]["style"]["stroke"] = "#000000"

    second = pipeline.run(changed, _viewport())

    assert first.profile.cache_key != second.profile.cache_key
    assert second.profile.cache_hit is False
    assert second.payload["viewport_pipeline"]["render_fingerprint"] != first.payload["viewport_pipeline"]["render_fingerprint"]


def test_invalidate_source_removes_only_matching_entries() -> None:
    pipeline = VisualizationViewportPipeline()
    source_a = _payload()
    source_b = _payload()
    source_b["las_id"] = "well-2"

    pipeline.run(source_a, _viewport())
    pipeline.run(source_b, _viewport())

    assert pipeline.invalidate_source(source_a) == 1
    assert pipeline.run(source_a, _viewport()).profile.cache_hit is False
    assert pipeline.run(source_b, _viewport()).profile.cache_hit is True


def test_invalidate_render_config_removes_matching_presets() -> None:
    pipeline = VisualizationViewportPipeline()
    source_a = _payload()
    source_b = _payload()
    source_b["las_id"] = "well-2"

    pipeline.run(source_a, _viewport())
    pipeline.run(source_b, _viewport())

    assert pipeline.invalidate_render_config(source_a) == 2
    assert pipeline.run(source_a, _viewport()).profile.cache_hit is False
    assert pipeline.run(source_b, _viewport()).profile.cache_hit is False


def test_viewport_cache_exposes_metrics() -> None:
    pipeline = VisualizationViewportPipeline()
    pipeline.run(_payload(), _viewport())
    second = pipeline.run(_payload(), _viewport())

    stats = second.payload["viewport_pipeline"]["cache_stats"]
    assert stats["entries"] == 1
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["invalidations"] == 0
