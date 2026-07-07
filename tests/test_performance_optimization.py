from __future__ import annotations

import time

from projects.performance_optimization import (
    build_cache_entry_table,
    build_optimization_recommendations,
    build_performance_manifest,
    build_performance_metric_table,
    cache_value,
    classify_metric_status,
    estimate_table_memory_bytes,
    get_cached_value,
    invalidate_cache,
    list_cache_entries,
    list_performance_metrics,
    measure_performance,
    record_performance_metric,
    summarize_performance,
)
from projects.repository import create_project


def test_record_metric_and_summary(tmp_path):
    project = create_project(tmp_path, "Perf Project")

    metric = record_performance_metric(
        tmp_path,
        project.id,
        {
            "name": "LAS import",
            "metric_type": "timer",
            "value": 1250,
            "unit": "ms",
            "component": "las_importer",
            "threshold_warning": 1000,
            "threshold_critical": 2000,
        },
    )

    assert metric.status == "warning"
    metrics = list_performance_metrics(tmp_path, project.id)
    assert len(metrics) == 1
    assert metrics[0].component == "las_importer"

    summary = summarize_performance(tmp_path, project.id)
    assert summary.metrics == 1
    assert summary.warnings == 1
    assert summary.slowest_metric_name == "LAS import"


def test_measure_performance_context_records_timer(tmp_path):
    project = create_project(tmp_path, "Timing Project")

    with measure_performance(tmp_path, project.id, "preview render", component="plot_studio") as state:
        sum(range(100))

    assert state["metric"] is not None
    metrics = list_performance_metrics(tmp_path, project.id, component="plot_studio")
    assert len(metrics) == 1
    assert metrics[0].metric_type == "timer"
    assert metrics[0].value >= 0


def test_cache_value_get_and_invalidate(tmp_path):
    project = create_project(tmp_path, "Cache Project")

    entry = cache_value(tmp_path, project.id, "las", "well-a:curves", {"GR": [1, 2, 3]})
    assert entry.size_bytes > 0
    assert get_cached_value(tmp_path, project.id, "las", "well-a:curves") == {"GR": [1, 2, 3]}

    entries = list_cache_entries(tmp_path, project.id)
    assert entries[0].hits == 1

    changed = invalidate_cache(tmp_path, project.id, namespace="las")
    assert changed == 1
    assert get_cached_value(tmp_path, project.id, "las", "well-a:curves") is None
    assert list_cache_entries(tmp_path, project.id)[0].status == "invalidated"


def test_cache_ttl_marks_stale(tmp_path):
    project = create_project(tmp_path, "TTL Project")
    cache_value(tmp_path, project.id, "plots", "preview", [1, 2, 3], ttl_seconds=0)
    time.sleep(0.01)

    assert get_cached_value(tmp_path, project.id, "plots", "preview") is None
    assert list_cache_entries(tmp_path, project.id)[0].status == "stale"


def test_recommendations_and_tables(tmp_path):
    project = create_project(tmp_path, "Recommendation Project")
    record_performance_metric(
        tmp_path,
        project.id,
        {
            "name": "Large DataFrame memory",
            "metric_type": "memory",
            "value": 900,
            "unit": "MB",
            "component": "statistics_center",
            "status": "critical",
        },
    )

    metrics = list_performance_metrics(tmp_path, project.id)
    recommendations = build_optimization_recommendations(metrics)
    assert len(recommendations) == 1
    assert "памяти" in recommendations[0].title

    assert build_performance_metric_table(metrics)[0]["Статус"] == "critical"
    assert build_cache_entry_table(list_cache_entries(tmp_path, project.id)) == []


def test_manifest_and_memory_estimation(tmp_path):
    project = create_project(tmp_path, "Manifest Project")
    cache_value(tmp_path, project.id, "dataframe", "sample", [{"a": 1}, {"a": 2}])
    record_performance_metric(tmp_path, project.id, {"name": "CSV export", "metric_type": "io", "value": 12})

    manifest = build_performance_manifest(tmp_path, project.id)
    assert manifest["schema"].endswith("v1")
    assert manifest["summary"]["metrics"] == 1
    assert len(manifest["cache"]) == 1
    assert estimate_table_memory_bytes([{"a": 1}]) > 0


def test_status_classifier():
    assert classify_metric_status(5, 10, 20) == "ok"
    assert classify_metric_status(12, 10, 20) == "warning"
    assert classify_metric_status(25, 10, 20) == "critical"
