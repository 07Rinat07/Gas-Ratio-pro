from __future__ import annotations

from threading import Event
from time import sleep

import pytest

from reports.background_export import BackgroundExportManager, ExportJobStatus


def _wait(manager: BackgroundExportManager, job_id: str, timeout: float = 2.0):
    remaining = timeout
    while remaining > 0:
        snapshot = manager.snapshot(job_id)
        if snapshot.terminal:
            return snapshot
        sleep(0.01)
        remaining -= 0.01
    raise AssertionError("background export did not finish")


def test_background_export_completes_and_returns_result():
    state = {}
    manager = BackgroundExportManager(state)

    def work(report, check_cancelled):
        report(20, "model")
        check_cancelled()
        report(80, "render")
        return b"%PDF-demo"

    created = manager.submit(project_id="p1", request_signature="sig-1", work=work)
    done = _wait(manager, created.id)

    assert done.status is ExportJobStatus.COMPLETED
    assert done.progress == 100
    assert manager.pop_result(created.id) == b"%PDF-demo"
    manager.shutdown()


def test_background_export_cancels_cooperatively():
    state = {}
    manager = BackgroundExportManager(state)
    entered = Event()

    def work(report, check_cancelled):
        entered.set()
        for index in range(100):
            report(index, "working")
            sleep(0.005)
            check_cancelled()
        return b"never"

    created = manager.submit(project_id="p1", request_signature="sig-cancel", work=work)
    assert entered.wait(1.0)
    manager.cancel(created.id)
    done = _wait(manager, created.id)

    assert done.status is ExportJobStatus.CANCELLED
    with pytest.raises(RuntimeError, match="ещё не готов"):
        manager.pop_result(created.id)
    manager.shutdown()


def test_duplicate_active_signature_is_rejected():
    state = {}
    manager = BackgroundExportManager(state)
    release = Event()

    def work(report, check_cancelled):
        release.wait(1.0)
        return "ok"

    manager.submit(project_id="p1", request_signature="same", work=work)
    with pytest.raises(RuntimeError, match="уже выполняется"):
        manager.submit(project_id="p1", request_signature="same", work=work)
    release.set()
    manager.shutdown(wait=True)


def test_recovery_marks_interrupted_job_as_orphaned():
    state = {
        BackgroundExportManager.STATE_KEY: {
            "job-1": {
                "id": "job-1",
                "project_id": "p1",
                "request_signature": "sig",
                "status": "running",
                "progress": 55,
                "message": "rendering",
                "created_at": 1.0,
                "updated_at": 2.0,
            }
        }
    }
    manager = BackgroundExportManager(state)
    recovered = manager.snapshot("job-1")

    assert recovered.status is ExportJobStatus.ORPHANED
    assert "перезапуском" in recovered.message
    manager.shutdown()


def test_progress_is_monotonic_and_snapshot_store_is_bounded(monkeypatch):
    state = {}
    manager = BackgroundExportManager(state)
    monkeypatch.setattr(manager, "MAX_SNAPSHOTS", 3)

    def work(report, check_cancelled):
        report(70, "later")
        report(20, "must not regress")
        return "ok"

    ids = []
    for index in range(5):
        created = manager.submit(project_id="p", request_signature=f"sig-{index}", work=work)
        ids.append(created.id)
        _wait(manager, created.id)

    snapshots = manager.list(project_id="p")
    assert len(snapshots) == 3
    assert all(snapshot.progress == 100 for snapshot in snapshots)
    manager.shutdown()


def test_export_controller_reports_background_stages_and_honours_cancellation():
    from reports.background_export import ExportCancelled
    from reports.export_controller import ExportArtifact, ExportController, ExportControllerError, ExportRequest

    request = ExportRequest(
        project_id="p1",
        project_name="Project",
        source_label="well.las",
        profile_id="engineering",
        format_id="pdf",
        format_label="PDF",
        extension="pdf",
        mime_type="application/pdf",
        depth_top=1000.0,
        depth_bottom=1100.0,
        source_signature="source",
        calculation_revision=1,
        presentation_revision=1,
        figure_height=1200,
    )
    progress = []
    cancelled = {"value": False}

    def check_cancelled():
        if cancelled["value"]:
            raise ExportCancelled("cancelled")

    def build_model(frame, export_request):
        progress.append((25, "builder"))
        cancelled["value"] = True
        return {"frame": frame}

    with pytest.raises(ExportCancelled):
        ExportController({}).prepare(
            request,
            frame=[1],
            build_model=build_model,
            render_artifact=lambda model, frame, req: ExportArtifact(
                content=b"%PDF-1.4\n",
                file_name="report.pdf",
                mime_type="application/pdf",
                format_id="pdf",
                format_label="PDF",
                profile_id="engineering",
            ),
            on_progress=lambda value, message: progress.append((value, message)),
            check_cancelled=check_cancelled,
        )

    assert any(value == 20 for value, _ in progress)
