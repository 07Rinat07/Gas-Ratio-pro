from pathlib import Path
import time

from core.data_platform.import_jobs import ImportJobManager
from core.data_platform.import_wizard import BatchImportItemResult, BatchImportResult


def _wait(manager, job_id, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = manager.get(job_id)
        if item.status in {"completed", "failed"}:
            return item
        time.sleep(0.01)
    raise AssertionError("job did not finish")


def test_job_is_compact_and_history_is_durable(tmp_path: Path):
    source = tmp_path / "well.las"
    source.write_text("~V\nVERS.2.0\n~A\n1000 1\n", encoding="utf-8")

    def runner(**kwargs):
        return BatchImportResult((BatchImportItemResult(source_name="well.las", status="success", dataset_id="ds-1", format_id="las", readiness_score=95),))

    manager = ImportJobManager(tmp_path / "projects", runner)
    submitted = manager.submit(project_id="default", sources=[source], actor="tester")
    finished = _wait(manager, submitted.job_id)
    assert finished.status == "completed"
    assert finished.success_count == 1
    assert finished.to_dict()["source_paths"] == [str(source.resolve())]
    history = manager.history("default")
    assert history[0]["job_id"] == submitted.job_id
    assert history[0]["result"]["items"][0]["readiness_score"] == 95


def test_retry_failed_items_only(tmp_path: Path):
    good = tmp_path / "good.las"; good.write_text("x", encoding="utf-8")
    bad = tmp_path / "bad.las"; bad.write_text("x", encoding="utf-8")
    calls = []
    def runner(**kwargs):
        paths = [Path(p) for p in kwargs["sources"]]
        calls.append([p.name for p in paths])
        if len(calls) == 1:
            return BatchImportResult((
                BatchImportItemResult(source_name="good.las", status="success"),
                BatchImportItemResult(source_name="bad.las", status="failed", error_code="Broken"),
            ))
        return BatchImportResult((BatchImportItemResult(source_name="bad.las", status="success"),))
    manager = ImportJobManager(tmp_path / "projects", runner)
    first = manager.submit(project_id="default", sources=[good, bad])
    _wait(manager, first.job_id)
    retry = manager.retry_failed(first.job_id)
    _wait(manager, retry.job_id)
    assert calls == [["good.las", "bad.las"], ["bad.las"]]
