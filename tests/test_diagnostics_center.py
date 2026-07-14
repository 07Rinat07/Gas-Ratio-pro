from core.cache_metrics import CacheMetricsRegistry
from core.diagnostics_center import build_diagnostics_center_snapshot
from core.runtime_diagnostics import RuntimeDiagnostics
from core.runtime_service_registry import runtime_service_registry
from core.repository_io import RepositoryIOMetrics


def test_diagnostics_center_returns_serializable_runtime_cache_and_session_data() -> None:
    state = {"workbench.route": "nav.correlation", "loose_key": 1}
    registry = runtime_service_registry(state)
    runtime = registry.ensure("runtime_diagnostics", RuntimeDiagnostics, expected_type=RuntimeDiagnostics)
    runtime.record(stage="las_correlation.total", duration_ms=12000, cache_status="miss")
    cache = registry.ensure("cache_metrics_registry", CacheMetricsRegistry, expected_type=CacheMetricsRegistry)
    counter = cache.counter("correlation_figure", max_entries=8)
    counter.hit(3)
    counter.miss(1)
    counter.set_entries(2)

    repository = registry.ensure("repository_io_metrics", RepositoryIOMetrics, expected_type=RepositoryIOMetrics)
    repository.record(repository="correlation", operation="read", status="success", duration_ms=3.5, bytes_count=120, path="correlation.json")

    snapshot = build_diagnostics_center_snapshot(
        state,
        performance_budgets_ms={"las_correlation.total": 10000},
    )

    assert snapshot["runtime"]["registry"]["active"] == 3
    assert snapshot["runtime"]["event_count"] == 1
    assert snapshot["cache"]["summary"]["hit_rate"] == 75.0
    assert snapshot["session"]["total_keys"] == 3
    assert snapshot["repository"]["reads"] == 1
    assert snapshot["repository"]["bytes_read"] == 120
    assert "loose_key" in snapshot["session"]["unscoped_keys"]
    assert snapshot["budgets"][0]["status"] == "slow"


def test_diagnostics_center_does_not_expose_runtime_instances() -> None:
    state = {}
    registry = runtime_service_registry(state)
    registry.set("runtime_diagnostics", RuntimeDiagnostics())

    snapshot = build_diagnostics_center_snapshot(state)

    assert snapshot["runtime"]["services"] == [
        {"key": "runtime_diagnostics", "type_name": "RuntimeDiagnostics"}
    ]
    assert all(not hasattr(value, "record") for value in snapshot["runtime"].values())
