from core.runtime_diagnostics import RuntimeDiagnostics


def test_stage_timer_records_success_and_failure() -> None:
    diagnostics = RuntimeDiagnostics(max_events=8)

    with diagnostics.timer(
        "correlation.panel",
        cache_status="miss",
        renderer="plotly",
        item_count=2,
    ):
        sum(range(20))

    try:
        with diagnostics.timer("correlation.failure"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    success, failed = diagnostics.snapshot()
    assert success.stage == "correlation.panel"
    assert success.status == "success"
    assert success.cache_status == "miss"
    assert success.item_count == 2
    assert success.duration_ms >= 0
    assert failed.status == "failed"


def test_cache_summary_reports_hit_rate_by_prefix() -> None:
    diagnostics = RuntimeDiagnostics(max_events=8)
    diagnostics.record(stage="correlation.cache", duration_ms=1, cache_status="hit")
    diagnostics.record(stage="correlation.cache", duration_ms=2, cache_status="miss")
    diagnostics.record(stage="interpretation.cache", duration_ms=3, cache_status="hit")

    summary = diagnostics.cache_summary(stage_prefix="correlation")

    assert summary == {"hits": 1, "misses": 1, "measured": 2, "hit_rate": 50.0}
