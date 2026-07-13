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
