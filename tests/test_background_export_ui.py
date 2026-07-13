from reports.background_export import ExportJobSnapshot, ExportJobStatus
from reports.background_export_ui import (
    build_background_export_status_view,
    latest_relevant_job,
)


def _snapshot(job_id: str, status: ExportJobStatus, *, signature: str = "sig", progress: int = 0):
    return ExportJobSnapshot(
        id=job_id,
        project_id="p1",
        request_signature=signature,
        status=status,
        progress=progress,
        message="message",
        created_at=1.0,
        updated_at=float(job_id[-1]) if job_id[-1].isdigit() else 1.0,
    )


def test_status_view_exposes_cancel_only_for_active_jobs():
    active = build_background_export_status_view(_snapshot("job-1", ExportJobStatus.RUNNING, progress=45))
    done = build_background_export_status_view(_snapshot("job-2", ExportJobStatus.COMPLETED, progress=100))

    assert active.progress == 45
    assert active.cancellable is True
    assert active.downloadable is False
    assert done.progress == 100
    assert done.cancellable is False
    assert done.downloadable is True


def test_failed_status_uses_safe_error_detail():
    snapshot = _snapshot("job-1", ExportJobStatus.FAILED, progress=70)
    snapshot = ExportJobSnapshot(**{**snapshot.to_dict(), "status": ExportJobStatus.FAILED, "error": "ValueError: broken"})
    view = build_background_export_status_view(snapshot)

    assert view.level == "error"
    assert "ValueError" in view.detail


def test_latest_relevant_job_prefers_active_matching_signature():
    newest_done = _snapshot("job-3", ExportJobStatus.COMPLETED, signature="sig")
    active = _snapshot("job-2", ExportJobStatus.RUNNING, signature="sig")
    other = _snapshot("job-4", ExportJobStatus.RUNNING, signature="other")

    selected = latest_relevant_job((other, newest_done, active), request_signature="sig")

    assert selected is active


def test_latest_relevant_job_returns_none_for_unrelated_signature():
    selected = latest_relevant_job(
        (_snapshot("job-1", ExportJobStatus.COMPLETED, signature="other"),),
        request_signature="sig",
    )
    assert selected is None


def test_completed_job_without_process_local_artifact_is_retryable():
    snapshot = _snapshot("job-5", ExportJobStatus.COMPLETED, progress=100)

    view = build_background_export_status_view(snapshot, artifact_available=False)

    assert view.level == "warning"
    assert view.downloadable is False
    assert view.retryable is True
    assert "перезапуска" in view.detail


def test_failed_cancelled_and_orphaned_jobs_are_retryable():
    for status in (
        ExportJobStatus.FAILED,
        ExportJobStatus.CANCELLED,
        ExportJobStatus.ORPHANED,
    ):
        view = build_background_export_status_view(_snapshot("job-6", status, progress=40))
        assert view.retryable is True
        assert view.cancellable is False
