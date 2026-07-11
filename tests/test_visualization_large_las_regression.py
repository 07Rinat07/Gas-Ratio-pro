from __future__ import annotations

from services.visualization_large_las_regression import VisualizationLargeLasRegression


def _large_payload(point_count: int = 50000) -> dict:
    start = 1000.0
    step = 0.01
    curves = []
    for curve_index, mnemonic in enumerate(("GR", "RHOB", "NPHI")):
        curves.append({
            "id": f"curve.{mnemonic}",
            "track_id": f"track.{curve_index}",
            "mnemonic": mnemonic,
            "unit": "API" if mnemonic == "GR" else "v/v",
            "scale_type": "linear",
            "range": {"min": 0.0, "max": 200.0},
            "points": [
                {"depth": start + index * step, "value": float((index * (curve_index + 3)) % 200)}
                for index in range(point_count)
            ],
        })
    return {
        "source_type": "las",
        "source_id": "large-las-regression",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": start, "stop": start + (point_count - 1) * step, "step": step},
        "tracks": [
            {"id": f"track.{index}", "title": title, "width": 1.0}
            for index, title in enumerate(("Gamma", "Density", "Neutron"))
        ],
        "curves": curves,
        "overlays": [],
        "performance_options": {"max_points_per_pixel": 1.0, "minimum_render_points": 32},
    }


def test_large_las_pipeline_is_bounded_downsampled_cached_and_exportable() -> None:
    report = VisualizationLargeLasRegression().run(_large_payload()).to_dict()

    assert report["ok"] is True, report["issues"]
    assert report["source_point_count"] == 150000
    assert report["render_point_count"] < report["source_point_count"]
    assert report["reduction_ratio"] >= 0.80
    assert report["peak_memory_bytes"] <= report["memory_limit_bytes"]
    assert report["cache_hit_on_repeat"] is True
    assert report["cache_bytes"] <= report["cache_max_bytes"]
    assert report["svg_bytes"] > 0
    assert report["pdf_bytes"] > 0
    assert report["geometry_signature_match"] is True
