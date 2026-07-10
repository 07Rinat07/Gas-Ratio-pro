from __future__ import annotations

from services.visualization_performance import (
    VisualizationPerformanceEngine,
    VisualizationRenderModelCache,
)
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload() -> dict:
    return {
        "source_type": "las",
        "source_id": "performance-demo",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1002.0, "step": 1.0},
        "tracks": [{"id": "track.gamma", "title": "Gamma", "width": 1.0}],
        "curves": [
            {
                "id": "curve.GR",
                "track_id": "track.gamma",
                "mnemonic": "GR",
                "unit": "API",
                "scale_type": "linear",
                "range": {"min": 0, "max": 150},
                "points": [
                    {"depth": 1000.0, "value": 40.0},
                    {"depth": 1001.0, "value": 55.0},
                    {"depth": 1002.0, "value": 70.0},
                ],
            }
        ],
        "overlays": [],
    }


def test_pipeline_reuses_cached_render_model_on_second_run() -> None:
    pipeline = VisualizationScenePipeline()

    first = pipeline.run(_payload()).to_dict()
    second = pipeline.run(_payload()).to_dict()

    assert first["performance"]["cache_hit"] is False
    assert second["performance"]["cache_hit"] is True
    assert len(first["performance"]["cache_key"]) == 64
    assert first["performance"]["cache_key"] == second["performance"]["cache_key"]
    assert first["render_model"] == second["render_model"]
    assert second["validation"]["performance_ok"] is True


def test_pipeline_can_disable_render_model_cache() -> None:
    payload = _payload()
    payload["performance_cache"] = False
    pipeline = VisualizationScenePipeline()

    first = pipeline.run(payload).to_dict()
    second = pipeline.run(payload).to_dict()

    assert first["performance"]["cache_enabled"] is False
    assert second["performance"]["cache_hit"] is False


def test_render_model_cache_is_bounded_and_lru() -> None:
    cache = VisualizationRenderModelCache(capacity=2)
    cache.put("a", {"schema": "a"})
    cache.put("b", {"schema": "b"})
    assert cache.get("a") == {"schema": "a"}
    cache.put("c", {"schema": "c"})

    assert cache.get("b") is None
    assert cache.get("a") == {"schema": "a"}
    assert cache.get("c") == {"schema": "c"}
    assert len(cache) == 2


def test_cache_key_changes_when_geometry_input_changes() -> None:
    engine = VisualizationPerformanceEngine()
    first = engine.cache_key({"width": 100}, {"tracks": [1]})
    second = engine.cache_key({"width": 101}, {"tracks": [1]})

    assert first != second
    assert len(first) == 64


def test_performance_options_change_cache_key_and_sampling_density() -> None:
    payload = _payload()
    payload["curves"][0]["points"] = [
        {"depth": 1000.0 + index * 0.001, "value": float(index % 150)}
        for index in range(2001)
    ]
    payload["depth_range"] = {"start": 1000.0, "stop": 1002.0, "step": 0.001}
    pipeline = VisualizationScenePipeline()

    compact = dict(payload)
    compact["performance_options"] = {
        "max_points_per_pixel": 0.5,
        "minimum_render_points": 16,
    }
    detailed = dict(payload)
    detailed["performance_options"] = {
        "max_points_per_pixel": 2.0,
        "minimum_render_points": 16,
    }

    compact_result = pipeline.run(compact).to_dict()
    detailed_result = pipeline.run(detailed).to_dict()

    assert compact_result["performance"]["cache_key"] != detailed_result["performance"]["cache_key"]
    assert compact_result["performance"]["render_point_count"] < detailed_result["performance"]["render_point_count"]


def test_cache_supports_targeted_invalidation() -> None:
    engine = VisualizationPerformanceEngine(VisualizationRenderModelCache(capacity=2))
    key = engine.cache_key({"scene": 1})
    engine.store(key, {"schema": "visualization.render.model"})

    assert engine.lookup(key) is not None
    assert engine.invalidate(key) is True
    assert engine.lookup(key) is None
    assert engine.invalidate(key) is False
