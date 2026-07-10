from __future__ import annotations

import pytest

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


def test_prefetch_populates_neighboring_viewports_without_rendering() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = True

    result = pipeline.run(payload, _viewport(1003.0, 1007.0))

    stats = result.payload["viewport_pipeline"]["cache_stats"]
    assert stats["prefetches"] == 2
    assert stats["entries"] == 3
    assert len(result.payload["viewport_pipeline"]["prefetch_keys"]) == 2


def test_prefetched_neighbor_becomes_payload_cache_hit() -> None:
    pipeline = VisualizationViewportPipeline()
    current = _viewport(1003.0, 1007.0)
    payload = _payload()
    payload["viewport_prefetch"] = True
    pipeline.run(payload, current)

    neighbor = current.pan_domain(current.domain_span * 0.75)
    result = pipeline.run(payload, neighbor)

    assert result.profile.cache_hit is True


def test_prefetch_can_be_disabled() -> None:
    payload = _payload()
    payload["viewport_prefetch"] = False
    pipeline = VisualizationViewportPipeline()

    result = pipeline.run(payload, _viewport())

    stats = result.payload["viewport_pipeline"]["cache_stats"]
    assert stats["prefetches"] == 0
    assert stats["entries"] == 1
    assert result.payload["viewport_pipeline"]["prefetch_keys"] == []


def test_prefetch_respects_domain_limits_and_skips_duplicate_viewport() -> None:
    pipeline = VisualizationViewportPipeline()
    viewport = _viewport(1000.0, 1004.0)
    payload = _payload()
    payload["viewport_prefetch"] = True

    result = pipeline.run(payload, viewport)

    stats = result.payload["viewport_pipeline"]["cache_stats"]
    assert stats["prefetch_skips"] >= 1


def test_prefetch_rejects_invalid_distance_ratio() -> None:
    payload = _payload()
    payload["viewport_prefetch"] = {"distance_ratio": 0}

    import pytest
    with pytest.raises(ValueError, match="distance_ratio"):
        VisualizationViewportPipeline().run(payload, _viewport())


def test_prefetch_scheduler_cancels_stale_navigation_work() -> None:
    from services.visualization_viewport_pipeline import (
        ViewportPrefetchTask,
        VisualizationViewportPrefetchScheduler,
    )

    scheduler = VisualizationViewportPrefetchScheduler(max_pending=4)
    generation = scheduler.begin_navigation()
    scheduler.schedule(
        ViewportPrefetchTask(
            generation=generation,
            key="old",
            viewport=_viewport(1002.0, 1006.0),
            direction="previous",
        )
    )

    scheduler.begin_navigation()

    assert len(scheduler) == 0
    assert scheduler.stats()["cancelled"] == 1


def test_prefetch_scheduler_limits_pending_queue() -> None:
    from services.visualization_viewport_pipeline import (
        ViewportPrefetchTask,
        VisualizationViewportPrefetchScheduler,
    )

    scheduler = VisualizationViewportPrefetchScheduler(max_pending=1)
    generation = scheduler.begin_navigation()
    scheduler.schedule(ViewportPrefetchTask(generation, "a", _viewport(), "previous"))
    scheduler.schedule(ViewportPrefetchTask(generation, "b", _viewport(), "next"))

    assert len(scheduler) == 1
    assert scheduler.stats()["cancelled"] == 1
    assert scheduler.pop_next().key == "b"


def test_prefetch_process_limit_leaves_cancellable_pending_work() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = {"process_limit": 1}

    first = pipeline.run(payload, _viewport(1003.0, 1007.0))
    assert first.payload["viewport_pipeline"]["prefetch_queue"]["pending"] == 1

    second = pipeline.run(payload, _viewport(1004.0, 1008.0))
    queue = second.payload["viewport_pipeline"]["prefetch_queue"]
    assert queue["cancelled"] >= 1
    assert queue["completed"] == 2


def test_prefetch_rejects_negative_process_limit() -> None:
    import pytest

    payload = _payload()
    payload["viewport_prefetch"] = {"process_limit": -1}

    with pytest.raises(ValueError, match="process_limit"):
        VisualizationViewportPipeline().run(payload, _viewport())


def test_prefetch_scheduler_prioritizes_navigation_direction() -> None:
    from services.visualization_viewport_pipeline import (
        ViewportPrefetchTask,
        VisualizationViewportPrefetchScheduler,
    )

    scheduler = VisualizationViewportPrefetchScheduler(max_pending=4)
    generation = scheduler.begin_navigation()
    scheduler.schedule(
        ViewportPrefetchTask(generation, "previous", _viewport(), "previous", priority=1, distance=3.0)
    )
    scheduler.schedule(
        ViewportPrefetchTask(generation, "next", _viewport(), "next", priority=0, distance=3.0)
    )

    assert scheduler.pop_next().key == "next"
    assert scheduler.stats()["priority_pops"] == 1


def test_prefetch_scheduler_prioritizes_nearest_task_with_equal_priority() -> None:
    from services.visualization_viewport_pipeline import (
        ViewportPrefetchTask,
        VisualizationViewportPrefetchScheduler,
    )

    scheduler = VisualizationViewportPrefetchScheduler(max_pending=4)
    generation = scheduler.begin_navigation()
    scheduler.schedule(
        ViewportPrefetchTask(generation, "far", _viewport(), "next", priority=0, distance=8.0)
    )
    scheduler.schedule(
        ViewportPrefetchTask(generation, "near", _viewport(), "next", priority=0, distance=2.0)
    )

    assert scheduler.pop_next().key == "near"


def test_pipeline_prefetch_follows_recent_pan_direction() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = {"process_limit": 1}

    pipeline.run(payload, _viewport(1002.0, 1006.0))
    result = pipeline.run(payload, _viewport(1003.0, 1007.0))

    queue = result.payload["viewport_pipeline"]["prefetch_queue"]
    assert queue["priority_pops"] >= 1
    assert len(result.payload["viewport_pipeline"]["prefetch_keys"]) == 1


def test_prefetch_adaptive_budget_reduces_work_under_queue_churn() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler(max_pending=4)
    scheduler.scheduled = 8
    scheduler.cancelled = 7

    limit = scheduler.adaptive_process_limit(
        {"entries": 1, "capacity": 16, "hits": 1, "misses": 5},
        base_limit=3,
    )

    assert limit == 1
    assert scheduler.stats()["last_process_budget"] == 1


def test_prefetch_adaptive_budget_stops_when_cache_is_full() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()

    assert scheduler.adaptive_process_limit(
        {"entries": 16, "capacity": 16, "hits": 10, "misses": 2},
        base_limit=3,
    ) == 0


def test_pipeline_uses_adaptive_prefetch_budget() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = {
        "adaptive_budget": True,
        "max_process_limit": 2,
    }

    result = pipeline.run(payload, _viewport(1003.0, 1007.0))

    queue = result.payload["viewport_pipeline"]["prefetch_queue"]
    assert queue["last_process_budget"] == 1
    assert len(result.payload["viewport_pipeline"]["prefetch_keys"]) == 1


def test_prefetch_rejects_negative_adaptive_budget_limit() -> None:
    import pytest

    payload = _payload()
    payload["viewport_prefetch"] = {
        "adaptive_budget": True,
        "max_process_limit": -1,
    }

    with pytest.raises(ValueError, match="max_process_limit"):
        VisualizationViewportPipeline().run(payload, _viewport())


def test_prefetch_cache_tracks_useful_hit_once() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = True
    current = _viewport(1003.0, 1007.0)
    pipeline.run(payload, current)

    neighbor = current.pan_domain(current.domain_span * 0.75)
    first = pipeline.run(payload, neighbor)
    second = pipeline.run(payload, neighbor)

    assert first.profile.cache_hit is True
    assert second.profile.cache_hit is True
    stats = second.payload["viewport_pipeline"]["cache_stats"]
    assert stats["prefetch_hits"] == 1
    assert stats["prefetch_hit_rate_ppm"] == 1_000_000


def test_prefetch_cache_tracks_unused_eviction() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPayloadCache

    cache = VisualizationViewportPayloadCache(capacity=1)
    prepared, profile = VisualizationViewportPipeline().prepare_payload(_payload(), _viewport())
    cache.put("prefetched", prepared, profile, prefetched=True)
    cache.put("regular", prepared, profile)

    stats = cache.stats()
    assert stats["prefetch_wasted"] == 1
    assert stats["prefetch_hit_rate_ppm"] == 0


def test_adaptive_prefetch_distance_expands_when_hits_are_useful() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    ratio = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 2},
        base_ratio=0.75,
    )

    assert ratio == 0.9375
    assert scheduler.stats()["last_distance_ratio"] == 0.9375


def test_adaptive_prefetch_distance_shrinks_when_work_is_wasted() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    ratio = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 1, "prefetch_wasted": 9},
        base_ratio=0.75,
    )

    assert ratio == 0.5625


def test_pipeline_exposes_adaptive_prefetch_distance() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = {
        "adaptive_distance": True,
        "process_limit": 1,
    }

    result = pipeline.run(payload, _viewport(1003.0, 1007.0))

    queue = result.payload["viewport_pipeline"]["prefetch_queue"]
    assert queue["last_distance_ratio"] == 0.75
    assert queue["distance_adjustments"] == 1


def test_adaptive_prefetch_distance_does_not_drift_on_repeated_counters() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    first = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 2},
        base_ratio=0.75,
    )
    second = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 2},
        base_ratio=0.75,
    )

    assert first == 0.9375
    assert second == first
    assert scheduler.stats()["telemetry_updates"] == 1
    assert scheduler.stats()["distance_holds"] == 1


def test_adaptive_prefetch_distance_ignores_small_noisy_window() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    baseline = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 0, "prefetch_wasted": 0},
        base_ratio=0.75,
    )
    noisy = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 1, "prefetch_wasted": 1},
        base_ratio=0.75,
        minimum_samples=4,
    )

    assert baseline == 0.75
    assert noisy == 0.75
    assert scheduler.stats()["telemetry_updates"] == 0


def test_pipeline_exposes_stabilized_prefetch_telemetry() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = {
        "adaptive_distance": True,
        "process_limit": 1,
        "minimum_telemetry_samples": 4,
        "telemetry_smoothing": 0.5,
    }

    result = pipeline.run(payload, _viewport(1003.0, 1007.0))
    queue = result.payload["viewport_pipeline"]["prefetch_queue"]

    assert queue["distance_holds"] == 1
    assert queue["telemetry_updates"] == 0
    assert queue["smoothed_prefetch_hit_rate_ppm"] == 0


def test_adaptive_prefetch_distance_respects_adjustment_cooldown() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    first = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 2},
        adjustment_cooldown_windows=1,
    )
    held = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 16, "prefetch_wasted": 4},
        adjustment_cooldown_windows=1,
    )
    third = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 24, "prefetch_wasted": 6},
        adjustment_cooldown_windows=1,
    )

    assert first == 0.9375
    assert held == first
    assert third > held
    assert scheduler.stats()["cooldown_holds"] == 1


def test_adaptive_prefetch_distance_requires_reverse_confirmation() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    expanded = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 0},
        smoothing=1.0,
        adjustment_cooldown_windows=0,
        reversal_confirmation_windows=2,
    )
    held = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 8},
        smoothing=1.0,
        adjustment_cooldown_windows=0,
        reversal_confirmation_windows=2,
    )
    shrunk = scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 16},
        smoothing=1.0,
        adjustment_cooldown_windows=0,
        reversal_confirmation_windows=2,
    )

    assert held == expanded
    assert shrunk < held
    assert scheduler.stats()["reversal_holds"] == 1
    assert scheduler.stats()["last_distance_direction"] == "shrink"


def test_pipeline_exposes_prefetch_anti_oscillation_metrics() -> None:
    pipeline = VisualizationViewportPipeline()
    payload = _payload()
    payload["viewport_prefetch"] = {
        "adaptive_distance": True,
        "process_limit": 1,
        "adjustment_cooldown_windows": 2,
        "reversal_confirmation_windows": 3,
    }

    result = pipeline.run(payload, _viewport(1003.0, 1007.0))
    queue = result.payload["viewport_pipeline"]["prefetch_queue"]

    assert queue["cooldown_holds"] == 0
    assert queue["reversal_holds"] == 0
    assert queue["last_distance_direction"] == ""


def test_prefetch_tuning_state_round_trip() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    scheduler.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 2},
        smoothing=1.0,
        adjustment_cooldown_windows=0,
    )
    snapshot = scheduler.tuning_state()

    restored = VisualizationViewportPrefetchScheduler()
    restored.restore_tuning_state(snapshot)

    assert restored.tuning_state() == snapshot
    assert restored.stats()["last_distance_ratio"] == scheduler.stats()["last_distance_ratio"]


def test_prefetch_tuning_state_preserves_cumulative_counter_baseline() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    scheduler.adaptive_distance_ratio({"prefetch_hits": 8, "prefetch_wasted": 2})
    snapshot = scheduler.tuning_state()

    restored = VisualizationViewportPrefetchScheduler()
    restored.restore_tuning_state(snapshot)
    ratio = restored.adaptive_distance_ratio(
        {"prefetch_hits": 8, "prefetch_wasted": 2},
        minimum_samples=4,
    )

    assert ratio == snapshot["last_distance_ratio"]
    assert restored.stats()["telemetry_updates"] == 0


def test_prefetch_tuning_state_rejects_invalid_contract() -> None:
    from services.visualization_viewport_pipeline import VisualizationViewportPrefetchScheduler

    scheduler = VisualizationViewportPrefetchScheduler()
    with pytest.raises(ValueError, match="schema"):
        scheduler.restore_tuning_state({"schema": "other", "version": "1.0"})
    with pytest.raises(ValueError, match="hit rate"):
        scheduler.restore_tuning_state({
            "schema": "visualization.viewport-prefetch-tuning",
            "version": "1.0",
            "smoothed_prefetch_hit_rate": 2.0,
        })
