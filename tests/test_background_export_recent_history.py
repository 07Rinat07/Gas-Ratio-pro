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
