from pathlib import Path
import json
import time

from core.data_platform.import_jobs import ImportJobManager, ImportJobSnapshot
from core.data_platform.import_wizard import BatchImportResult


def test_restart_recovers_active_job_as_interrupted(tmp_path: Path):
    root = tmp_path / "projects"
    source = root / "default" / "imports" / "staging" / "well.las"
    source.parent.mkdir(parents=True)
    source.write_text("x", encoding="utf-8")
    snapshot = ImportJobSnapshot(
        job_id="import-recover",
        project_id="default",
        source_paths=(str(source.resolve()),),
        source_names=("well.las",),
        status="running",
        created_at="2026-01-01T00:00:00+00:00",
    )
    jobs_path = root / "default" / "imports" / "jobs.json"
    jobs_path.write_text(json.dumps([snapshot.to_dict()]), encoding="utf-8")

    manager = ImportJobManager(root, lambda **kwargs: BatchImportResult(()))
    recovered = manager.get("import-recover")
    assert recovered.status == "interrupted"
    assert recovered.error_code == "ImportJobInterrupted"
    assert manager.history("default")[0]["status"] == "interrupted"


def test_history_filter_export_and_staging_cleanup(tmp_path: Path):
    root = tmp_path / "projects"
    manager = ImportJobManager(root, lambda **kwargs: BatchImportResult(()))
    history = manager._history
    history.append(ImportJobSnapshot(job_id="a", project_id="default", source_paths=(), source_names=("alpha.las",), status="completed"))
    history.append(ImportJobSnapshot(job_id="b", project_id="default", source_paths=(), source_names=("broken.las",), status="failed"))

    filtered = manager.history("default", statuses={"failed"}, query="broken")
    assert [item["job_id"] for item in filtered] == ["b"]
    assert b'"job_id": "b"' in manager.export_history("default", format_id="json", statuses={"failed"})
    assert "job_id,status" in manager.export_history("default", format_id="csv").decode("utf-8-sig")

    staging = root / "default" / "imports" / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    stale = staging / "stale.las"
    stale.write_bytes(b"123")
    result = manager.cleanup_staging("default")
    assert result == {"removed_files": 1, "removed_bytes": 3}
    assert not stale.exists()


def test_running_job_accepts_cancellation_request(tmp_path: Path):
    source = tmp_path / "well.las"
    source.write_text("x", encoding="utf-8")

    def runner(**kwargs):
        time.sleep(0.1)
        return BatchImportResult(())

    manager = ImportJobManager(tmp_path / "projects", runner)
    job = manager.submit(project_id="default", sources=[source])
    deadline = time.time() + 2
    while time.time() < deadline and manager.get(job.job_id).status == "queued":
        time.sleep(0.005)
    cancelled = manager.cancel(job.job_id)
    assert cancelled.status in {"cancel_requested", "cancelled"}
    deadline = time.time() + 2
    while time.time() < deadline and manager.get(job.job_id).status not in {"cancelled", "completed"}:
        time.sleep(0.01)
    assert manager.get(job.job_id).status == "cancelled"
