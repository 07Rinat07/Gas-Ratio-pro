from reports.background_export import ExportJobSnapshot, ExportJobStatus
from reports.background_export_ui import (
    build_recent_background_job_history,
    retry_diagnostic_reason,
)


def _snapshot(job_id: str, status: ExportJobStatus, *, updated_at: float, retry_reason: str = ""):
    return ExportJobSnapshot(
        id=job_id,
        project_id="p1",
        request_signature=f"sig-{job_id}",
        status=status,
        progress=100 if status is ExportJobStatus.COMPLETED else 40,
        message="message",
        created_at=updated_at - 1,
        updated_at=updated_at,
        error="ValueError: broken" if status is ExportJobStatus.FAILED else "",
        retry_reason=retry_reason,
    )


def test_recent_background_history_is_bounded_and_keeps_retry_diagnostics():
    snapshots = tuple(
        _snapshot(f"job-{index}", ExportJobStatus.FAILED, updated_at=float(10 - index), retry_reason=f"reason-{index}")
        for index in range(8)
    )

    items = build_recent_background_job_history(snapshots, limit=5)

    assert len(items) == 5
    assert [item.job_id for item in items] == [f"job-{index}" for index in range(5)]
    assert items[0].retry_reason == "reason-0"
    assert all(item.retryable for item in items)


def test_retry_diagnostic_reason_covers_failure_cancel_restart_and_lost_artifact():
    assert "ValueError" in retry_diagnostic_reason(_snapshot("f", ExportJobStatus.FAILED, updated_at=1))
    assert "отмен" in retry_diagnostic_reason(_snapshot("c", ExportJobStatus.CANCELLED, updated_at=1)).lower()
    assert "перезапуск" in retry_diagnostic_reason(_snapshot("o", ExportJobStatus.ORPHANED, updated_at=1)).lower()
    completed = _snapshot("d", ExportJobStatus.COMPLETED, updated_at=1)
    assert "утрачен" in retry_diagnostic_reason(completed, artifact_available=False).lower()


def test_background_manager_persists_retry_metadata():
    from reports.background_export import BackgroundExportManager

    state = {}
    manager = BackgroundExportManager(state)
    job = manager.submit(
        project_id="p1",
        request_signature="sig",
        retry_of_job_id="old-job",
        retry_reason="old export failed",
        work=lambda report, check: b"ok",
    )
    snapshot = manager.snapshot(job.id)
    assert snapshot.retry_of_job_id == "old-job"
    assert snapshot.retry_reason == "old export failed"
    manager.shutdown(wait=True)


def test_history_cleanup_protects_unclaimed_completed_artifact():
    completed = _snapshot("ready", ExportJobStatus.COMPLETED, updated_at=3)
    failed = _snapshot("failed", ExportJobStatus.FAILED, updated_at=2)

    items = build_recent_background_job_history(
        (completed, failed),
        artifact_availability={"ready": True, "failed": False},
    )

    assert items[0].terminal is True
    assert items[0].dismissible is False
    assert items[1].terminal is True
    assert items[1].dismissible is True


def test_history_filter_supports_status_and_format_without_reordering():
    from dataclasses import replace
    from reports.background_export_ui import filter_recent_background_job_history

    snapshots = (
        replace(_snapshot("pdf-ok", ExportJobStatus.COMPLETED, updated_at=3), export_format="pdf"),
        replace(_snapshot("docx-fail", ExportJobStatus.FAILED, updated_at=2), export_format="docx"),
        replace(_snapshot("pdf-fail", ExportJobStatus.FAILED, updated_at=1), export_format="pdf"),
    )
    items = build_recent_background_job_history(snapshots)

    filtered = filter_recent_background_job_history(
        items,
        statuses=(ExportJobStatus.FAILED,),
        formats=("PDF",),
    )

    assert [item.job_id for item in filtered] == ["pdf-fail"]
    assert filter_recent_background_job_history(items) == items


def test_completed_job_persists_duration_and_artifact_size():
    from reports.background_export import BackgroundExportManager

    state = {}
    manager = BackgroundExportManager(state)
    job = manager.submit(
        project_id="p1",
        request_signature="sized-result",
        export_format="pdf",
        work=lambda report, check: b"engineering-report",
    )
    manager.shutdown(wait=True)

    snapshot = manager.snapshot(job.id)
    assert snapshot.status is ExportJobStatus.COMPLETED
    assert snapshot.duration_seconds >= 0.0
    assert snapshot.artifact_size_bytes == len(b"engineering-report")

    restored = ExportJobSnapshot.from_dict(snapshot.to_dict())
    assert restored.duration_seconds == snapshot.duration_seconds
    assert restored.artifact_size_bytes == snapshot.artifact_size_bytes


def test_history_exposes_duration_and_artifact_size_with_backward_compatibility():
    from dataclasses import replace

    current = replace(
        _snapshot("sized", ExportJobStatus.COMPLETED, updated_at=12),
        created_at=2,
        duration_seconds=7.5,
        artifact_size_bytes=2 * 1024 * 1024,
    )
    legacy = _snapshot("legacy", ExportJobStatus.FAILED, updated_at=8)

    items = build_recent_background_job_history((current, legacy))

    assert items[0].duration_seconds == 7.5
    assert items[0].artifact_size_bytes == 2 * 1024 * 1024
    assert items[1].duration_seconds == 1.0
    assert items[1].artifact_size_bytes == 0


def test_duration_and_artifact_size_formatters_are_compact_and_safe():
    from reports.background_export_ui import format_artifact_size, format_export_duration

    assert format_export_duration(-1) == "0 с"
    assert format_export_duration(59.4) == "59 с"
    assert format_export_duration(61) == "1 мин 01 с"
    assert format_export_duration(3661) == "1 ч 01 мин"
    assert format_artifact_size(-1) == "0 Б"
    assert format_artifact_size(1024) == "1.0 КиБ"
    assert format_artifact_size(2 * 1024 * 1024) == "2.0 МиБ"


def test_history_sort_supports_time_duration_and_size_with_stable_ties():
    from dataclasses import replace
    from reports.background_export_ui import sort_recent_background_job_history

    items = build_recent_background_job_history((
        replace(
            _snapshot("new-small", ExportJobStatus.COMPLETED, updated_at=30),
            duration_seconds=2,
            artifact_size_bytes=100,
        ),
        replace(
            _snapshot("old-large", ExportJobStatus.COMPLETED, updated_at=10),
            duration_seconds=8,
            artifact_size_bytes=5000,
        ),
        replace(
            _snapshot("mid-medium", ExportJobStatus.COMPLETED, updated_at=20),
            duration_seconds=5,
            artifact_size_bytes=1000,
        ),
    ))

    assert [item.job_id for item in sort_recent_background_job_history(items)] == [
        "new-small", "mid-medium", "old-large"
    ]
    assert [item.job_id for item in sort_recent_background_job_history(items, sort_by="updated_asc")] == [
        "old-large", "mid-medium", "new-small"
    ]
    assert [item.job_id for item in sort_recent_background_job_history(items, sort_by="duration_desc")] == [
        "old-large", "mid-medium", "new-small"
    ]
    assert [item.job_id for item in sort_recent_background_job_history(items, sort_by="size_asc")] == [
        "new-small", "mid-medium", "old-large"
    ]


def test_history_sort_unknown_mode_falls_back_to_newest_first():
    from reports.background_export_ui import sort_recent_background_job_history

    items = build_recent_background_job_history((
        _snapshot("older", ExportJobStatus.FAILED, updated_at=1),
        _snapshot("newer", ExportJobStatus.FAILED, updated_at=2),
    ))

    sorted_items = sort_recent_background_job_history(items, sort_by="unsupported")
    assert [item.job_id for item in sorted_items] == ["newer", "older"]


def test_performance_summary_aggregates_terminal_jobs_only():
    from dataclasses import replace
    from reports.background_export_ui import build_background_export_performance_summary

    items = build_recent_background_job_history((
        replace(
            _snapshot("ok-1", ExportJobStatus.COMPLETED, updated_at=10),
            created_at=5,
            duration_seconds=5,
            artifact_size_bytes=1024,
        ),
        replace(
            _snapshot("ok-2", ExportJobStatus.COMPLETED, updated_at=20),
            created_at=10,
            duration_seconds=10,
            artifact_size_bytes=3072,
        ),
        replace(
            _snapshot("failed", ExportJobStatus.FAILED, updated_at=30),
            created_at=15,
            duration_seconds=15,
        ),
        _snapshot("running", ExportJobStatus.RUNNING, updated_at=40),
    ))

    summary = build_background_export_performance_summary(items)

    assert summary.total_jobs == 4
    assert summary.active_jobs == 1
    assert summary.completed_jobs == 2
    assert summary.failed_jobs == 1
    assert summary.success_rate_percent == 200 / 3
    assert summary.average_duration_seconds == 10
    assert summary.average_artifact_size_bytes == 2048


def test_performance_summary_is_safe_for_empty_or_active_only_history():
    from reports.background_export_ui import build_background_export_performance_summary

    empty = build_background_export_performance_summary(())
    active = build_background_export_performance_summary(
        build_recent_background_job_history((
            _snapshot("running", ExportJobStatus.RUNNING, updated_at=2),
        ))
    )

    assert empty.total_jobs == 0
    assert empty.success_rate_percent == 0.0
    assert empty.average_duration_seconds == 0.0
    assert active.active_jobs == 1
    assert active.success_rate_percent == 0.0
