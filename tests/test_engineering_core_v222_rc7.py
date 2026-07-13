from __future__ import annotations

import plotly.graph_objects as go

from core.application_state import ApplicationStateController
from core.runtime_diagnostics import RuntimeDiagnostics
from palettes.plot_cache import PlotCache


def test_application_state_namespaces_are_isolated() -> None:
    state: dict[str, object] = {}
    controller = ApplicationStateController(state)
    controller.update_namespace("plots", {"revision": 3})
    controller.update_namespace("export", {"format": "pdf"})
    assert controller.get_namespace("plots") == {"revision": 3}
    assert controller.get_namespace("export") == {"format": "pdf"}
    assert controller.clear_namespace("plots") == {"revision": 3}
    assert controller.get_namespace("plots") == {}
    assert controller.get_namespace("export") == {"format": "pdf"}


def test_plot_cache_reports_hits_misses_evictions_and_memory() -> None:
    cache = PlotCache(max_entries=1)
    assert cache.get("missing") is None
    cache.put("a", [go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])])
    assert cache.get("a") is not None
    cache.put("b", [go.Figure(data=[go.Scatter(x=[1], y=[2])])])
    stats = cache.stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.puts == 2
    assert stats.evictions == 1
    assert stats.entries == 1
    assert stats.estimated_bytes > 0


def test_runtime_diagnostics_is_bounded_and_stage_filterable() -> None:
    diagnostics = RuntimeDiagnostics(max_events=2)
    diagnostics.record(stage="load", duration_ms=2.5)
    diagnostics.record(stage="plots", duration_ms=10.0, cache_status="miss", item_count=5)
    diagnostics.record(stage="plots", duration_ms=0.5, cache_status="hit", item_count=5)
    assert len(diagnostics) == 2
    latest = diagnostics.latest("plots")
    assert latest is not None
    assert latest.cache_status == "hit"
    assert latest.item_count == 5
