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
    assert "preview_counts_repository.load(str(active_project.id))" in source
    assert "preview_counts_repository.save(" in source
    assert "preview_counts_repository.delete(str(active_project.id))" in source
