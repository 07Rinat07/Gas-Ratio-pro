from __future__ import annotations

import json

import pytest

from reports.report_designer import ReportDocumentCounts, build_report_document_counts_snapshot
from reports.report_preview_persistence import ReportPreviewCountsRepository


def _snapshot(signature: str = "abc") -> dict[str, object]:
    return build_report_document_counts_snapshot(
        ReportDocumentCounts(sections=5, tables=3, table_rows=81, plots=4, visualizations=2, notices=1),
        signature=signature,
        generated_at="2026-07-14T00:00:00+00:00",
    )


def test_repository_round_trip_is_project_scoped(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    payload = _snapshot()

    path = repository.save("project-1", payload)

    assert path == tmp_path / "project-1" / "report_preview_counts.json"
    assert repository.load("project-1") == payload
    assert repository.load("project-2") is None


def test_repository_rejects_invalid_snapshot(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)

    with pytest.raises(ValueError, match="invalid report preview snapshot"):
        repository.save("project-1", {"schema": 1, "signature": "abc", "counts": "broken"})


def test_repository_uses_atomic_temporary_file(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    path = repository.save("project-1", _snapshot())

    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
    assert json.loads(path.read_text(encoding="utf-8"))["signature"] == "abc"


def test_repository_delete_is_idempotent(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    repository.save("project-1", _snapshot())

    assert repository.delete("project-1") is True
    assert repository.delete("project-1") is False


def test_repository_sanitizes_project_identifier(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)

    assert repository.path_for(" project/unsafe ") == tmp_path / "project_unsafe" / "report_preview_counts.json"
    with pytest.raises(ValueError, match="project_id is required"):
        repository.path_for(" .. ")


def test_streamlit_integrates_project_persistence():
    source = open("app/streamlit_app.py", encoding="utf-8").read()

    assert "ReportPreviewCountsRepository(ROOT_DIR / \"data\" / \"projects\")" in source
    assert "preview_counts_repository.load_with_recovery(str(active_project.id))" in source
    assert "preview_counts_repository.save(" in source
    assert "preview_counts_repository.delete(str(active_project.id), include_quarantine=True)" in source


def test_repository_keeps_previous_valid_snapshot_as_backup(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    repository.save("project-1", _snapshot("first"))
    repository.save("project-1", _snapshot("second"))

    backup = repository.backup_path_for("project-1")
    assert backup.exists()
    assert json.loads(backup.read_text(encoding="utf-8"))["signature"] == "first"
    assert repository.load("project-1")["signature"] == "second"


def test_repository_recovers_corrupt_primary_from_backup(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    repository.save("project-1", _snapshot("first"))
    repository.save("project-1", _snapshot("second"))
    repository.path_for("project-1").write_text("{broken", encoding="utf-8")

    result = repository.load_with_recovery("project-1")

    assert result.recovered is True
    assert result.source == "backup"
    assert result.payload["signature"] == "first"
    assert repository.load("project-1")["signature"] == "first"
    assert result.quarantined


def test_repository_quarantines_primary_and_backup_when_both_are_invalid(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    primary = repository.path_for("project-1")
    backup = repository.backup_path_for("project-1")
    primary.parent.mkdir(parents=True)
    primary.write_text("not-json", encoding="utf-8")
    backup.write_text("[]", encoding="utf-8")

    result = repository.load_with_recovery("project-1")

    assert result.payload is None
    assert result.source == "quarantined"
    assert len(result.quarantined) == 2
    assert not primary.exists()
    assert not backup.exists()


def test_repository_delete_removes_primary_and_backup(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    repository.save("project-1", _snapshot("first"))
    repository.save("project-1", _snapshot("second"))

    assert repository.delete("project-1") is True
    assert not repository.path_for("project-1").exists()
    assert not repository.backup_path_for("project-1").exists()


def _write_quarantine_files(repository, project_id: str, count: int):
    directory = repository.path_for(project_id).parent
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in range(count):
        path = directory / f"report_preview_counts.json.corrupt-20260714T00000000000{index}Z"
        path.write_text(f"broken-{index}", encoding="utf-8")
        # Deterministic ordering independent from filesystem timestamp resolution.
        path.touch()
        paths.append(path)
    return paths


def test_repository_quarantine_retention_is_bounded(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path, max_quarantine_files=2)
    paths = _write_quarantine_files(repository, "project-1", 5)

    result = repository.maintain_quarantine("project-1")

    assert len(result.kept) == 2
    assert len(result.removed) == 3
    assert len(repository.quarantine_paths("project-1")) == 2
    assert all(not path.exists() for path in paths[:3])


def test_repository_can_disable_quarantine_retention(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path, max_quarantine_files=0)
    _write_quarantine_files(repository, "project-1", 3)

    result = repository.maintain_quarantine("project-1")

    assert result.kept == ()
    assert len(result.removed) == 3
    assert repository.quarantine_paths("project-1") == ()


def test_repository_purge_quarantine_is_project_scoped(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    _write_quarantine_files(repository, "project-1", 2)
    _write_quarantine_files(repository, "project-2", 1)

    removed = repository.purge_quarantine("project-1")

    assert len(removed) == 2
    assert repository.quarantine_paths("project-1") == ()
    assert len(repository.quarantine_paths("project-2")) == 1


def test_repository_delete_can_include_quarantine(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    repository.save("project-1", _snapshot())
    _write_quarantine_files(repository, "project-1", 2)

    assert repository.delete("project-1", include_quarantine=True) is True
    assert repository.quarantine_paths("project-1") == ()
    assert not repository.path_for("project-1").exists()


def test_repository_storage_health_reports_empty_project(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)

    health = repository.storage_health("project-1")

    assert health.status == "empty"
    assert health.primary_exists is False
    assert health.backup_exists is False
    assert health.quarantine_count == 0
    assert health.total_bytes == 0


def test_repository_storage_health_reports_valid_primary_and_backup(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    repository.save("project-1", _snapshot("first"))
    repository.save("project-1", _snapshot("second"))

    health = repository.storage_health("project-1")

    assert health.status == "healthy"
    assert health.primary_valid is True
    assert health.backup_valid is True
    assert health.total_bytes > 0


def test_repository_storage_health_reports_recoverable_primary(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    repository.save("project-1", _snapshot("first"))
    repository.save("project-1", _snapshot("second"))
    repository.path_for("project-1").write_text("{broken", encoding="utf-8")

    health = repository.storage_health("project-1")

    assert health.status == "recoverable"
    assert health.primary_exists is True
    assert health.primary_valid is False
    assert health.backup_valid is True


def test_repository_storage_health_includes_quarantine_usage(tmp_path):
    repository = ReportPreviewCountsRepository(tmp_path)
    paths = _write_quarantine_files(repository, "project-1", 2)

    health = repository.storage_health("project-1")

    assert health.status == "quarantined"
    assert health.quarantine_count == 2
    assert health.quarantine_bytes == sum(path.stat().st_size for path in paths)
    assert health.total_bytes == health.quarantine_bytes


def test_streamlit_shows_report_preview_storage_health():
    source = open("app/streamlit_app.py", encoding="utf-8").read()

    assert "preview_counts_repository.storage_health(str(active_project.id))" in source
    assert "Состояние хранилища предпросмотра" in source
