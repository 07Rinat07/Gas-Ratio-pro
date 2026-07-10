from services.visualization_curve_quality import VisualizationCurveQualityEngine


def test_curve_quality_splits_missing_values_and_large_depth_gaps():
    result = VisualizationCurveQualityEngine().build(
        layer_id="curve.GR",
        points=[
            {"depth": 1000, "value": 10},
            {"depth": 1001, "value": 20},
            {"depth": 1002, "value": None},
            {"depth": 1003, "value": 30},
            {"depth": 1004, "value": 40},
            {"depth": 1050, "value": 50},
            {"depth": 1051, "value": 60},
        ],
        axis_min=0,
        axis_max=100,
        scale="linear",
        depth_start=1000,
        depth_stop=1100,
        plot_x=10,
        plot_y=50,
        plot_width=200,
        plot_height=600,
    )

    assert len(result.segments) == 3
    assert result.metadata["invalid_point_count"] == 1
    assert result.metadata["gap_break_count"] == 1
    assert all(len(segment.points) == 2 for segment in result.segments)


def test_curve_quality_rejects_non_positive_log_values_without_bridge_line():
    result = VisualizationCurveQualityEngine().build(
        layer_id="curve.RES",
        points=[
            {"depth": 1000, "value": 1},
            {"depth": 1001, "value": 10},
            {"depth": 1002, "value": 0},
            {"depth": 1003, "value": 100},
            {"depth": 1004, "value": 1000},
        ],
        axis_min=1,
        axis_max=1000,
        scale="log",
        depth_start=1000,
        depth_stop=1010,
        plot_x=0,
        plot_y=0,
        plot_width=100,
        plot_height=200,
    )

    assert len(result.segments) == 2
    assert result.metadata["invalid_point_count"] == 1


def test_curve_quality_clips_points_outside_depth_viewport():
    result = VisualizationCurveQualityEngine().build(
        layer_id="curve.GR",
        points=[
            {"depth": 990, "value": 10},
            {"depth": 1000, "value": 20},
            {"depth": 1001, "value": 30},
            {"depth": 1110, "value": 40},
        ],
        axis_min=0,
        axis_max=100,
        scale="linear",
        depth_start=1000,
        depth_stop=1100,
        plot_x=0,
        plot_y=0,
        plot_width=100,
        plot_height=200,
    )

    assert len(result.segments) == 1
    assert result.metadata["clipped_point_count"] == 2


def test_curve_quality_adaptively_downsamples_dense_viewport_and_preserves_endpoints():
    engine = VisualizationCurveQualityEngine()
    points = [
        {"depth": 1000.0 + index * 0.01, "value": float((index % 40) - 20)}
        for index in range(2000)
    ]

    result = engine.build(
        layer_id="curve.dense",
        points=points,
        axis_min=-25.0,
        axis_max=25.0,
        scale="linear",
        depth_start=1000.0,
        depth_stop=1019.99,
        plot_x=0.0,
        plot_y=0.0,
        plot_width=200.0,
        plot_height=120.0,
        max_points_per_pixel=1.0,
        minimum_render_points=32,
    )

    assert result.ok is True
    assert result.metadata["sampling_strategy"] == "viewport_extrema"
    assert result.metadata["point_budget"] == 120
    assert result.metadata["render_point_count"] <= 120
    assert result.metadata["downsampled_point_count"] > 0
    segment = result.segments[0]
    assert segment.points[0]["y"] == 0.0
    assert segment.points[-1]["y"] == 120.0
