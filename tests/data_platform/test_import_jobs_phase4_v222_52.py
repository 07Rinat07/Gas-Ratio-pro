from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import time

from core.data_platform.import_jobs import ImportJobManager
from core.data_platform.import_wizard import BatchImportItemResult, BatchImportResult


def _wait(manager: ImportJobManager, job_id: str, timeout: float = 3.0):
    end = time.time() + timeout
    while time.time() < end:
        item = manager.get(job_id)
        if item.status in {"completed", "failed", "cancelled", "interrupted"}:
            return item
        time.sleep(0.01)
    raise AssertionError("job did not finish")


def test_cooperative_cancel_stops_between_batch_items(tmp_path: Path):
    processed: list[str] = []

    def runner(*, project_id, sources, actor, should_cancel=None, progress_callback=None):
        items = []
        for index, raw in enumerate(sources):
            if should_cancel and should_cancel():
                break
            processed.append(Path(raw).name)
            time.sleep(0.03)
            items.append(BatchImportItemResult(source_name=Path(raw).name, status="success"))
            if progress_callback:
                progress_callback(index + 1, len(sources))
        return BatchImportResult(tuple(items))

    sources = []
    for index in range(5):
        path = tmp_path / f"f{index}.las"
        path.write_text("x", encoding="utf-8")
        sources.append(path)
    manager = ImportJobManager(tmp_path / "projects", runner)
    job = manager.submit(project_id="default", sources=sources)
    time.sleep(0.055)
    manager.cancel(job.job_id)
    final = _wait(manager, job.job_id)
    assert final.status == "cancelled"
    assert len(processed) < len(sources)


def test_resume_interrupted_requires_explicit_user_action(tmp_path: Path):
    root = tmp_path / "projects"
    source = tmp_path / "a.las"
    source.write_text("x", encoding="utf-8")
    jobs = root / "default" / "imports" / "jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text(json.dumps([{
        "job_id": "import-old", "project_id": "default", "source_paths": [str(source)],
        "source_names": [source.name], "status": "running", "created_at": datetime.now(timezone.utc).isoformat()
    }]), encoding="utf-8")

    manager = ImportJobManager(root, lambda **_: BatchImportResult(()))
    assert manager.get("import-old").status == "interrupted"
    resumed = manager.resume_interrupted("import-old")
    assert resumed.job_id != "import-old"
    assert resumed.status == "queued"


def test_retention_policy_prunes_old_history_and_staging(tmp_path: Path):
    root = tmp_path / "projects"
    history = root / "default" / "imports" / "history.jsonl"
    history.parent.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    history.write_text(
        json.dumps({"job_id": "old", "project_id": "default", "status": "completed", "finished_at": old}) + "\n" +
        json.dumps({"job_id": "new", "project_id": "default", "status": "completed", "finished_at": recent}) + "\n",
        encoding="utf-8",
    )
    staging = root / "default" / "imports" / "staging"
    staging.mkdir()
    stale = staging / "stale.las"
    stale.write_text("old", encoding="utf-8")
    old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(stale, (old_ts, old_ts))

    manager = ImportJobManager(root, lambda **_: BatchImportResult(()))
    result = manager.apply_retention_policy("default", retention_days=90, keep_latest=1, staging_max_age_days=7)
    assert result["removed_entries"] == 1
    assert result["removed_staging_files"] == 1
    assert not stale.exists()
