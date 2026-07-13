from pathlib import Path
import json

import pytest

from reports.export_history import (
    EXPORT_HISTORY_SCHEMA,
    ExportHistoryEntry,
    ExportHistoryRepository,
)


def _entry(project_id: str = "project/alpha", *, index: int = 1) -> ExportHistoryEntry:
    return ExportHistoryEntry(
        project_id=project_id,
        file_name=f"report_{index}.pdf",
        format_id="PDF",
        format_label="PDF",
        profile_id="Engineering",
        depth_top=2200.0,
        depth_bottom=2100.0,
        size_bytes=1024 * index,
        request_signature=f"signature-{index}",
        cache_hit=index % 2 == 0,
    )


def test_history_round_trip_is_project_scoped_atomic_and_normalized(tmp_path: Path) -> None:
    repository = ExportHistoryRepository(tmp_path, max_entries=5)
    path = repository.record(_entry())

    assert path.name == "export_history.json"
    assert path.parent.name == "project_alpha"
    assert not path.with_suffix(".json.tmp").exists()

    restored = repository.load("project/alpha")
    assert len(restored) == 1
    assert restored[0].format_id == "pdf"
    assert restored[0].profile_id == "engineering"
    assert restored[0].depth_top == 2100.0
    assert restored[0].depth_bottom == 2200.0
    assert restored[0].created_at


def test_history_is_bounded_newest_first_and_deduplicates_signature(tmp_path: Path) -> None:
    repository = ExportHistoryRepository(tmp_path, max_entries=3)
    for index in range(1, 5):
        repository.record(_entry(index=index))
    repository.record(_entry(index=4))

    restored = repository.load("project/alpha")
    assert [item.file_name for item in restored] == ["report_4.pdf", "report_3.pdf", "report_2.pdf"]


def test_history_file_contains_metadata_only(tmp_path: Path) -> None:
    repository = ExportHistoryRepository(tmp_path)
    path = repository.record(_entry())
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema"] == EXPORT_HISTORY_SCHEMA
    serialized = path.read_text(encoding="utf-8").lower()
    assert "content" not in serialized
    assert "dataframe" not in serialized
    assert "rendered" not in serialized


def test_clear_is_idempotent(tmp_path: Path) -> None:
    repository = ExportHistoryRepository(tmp_path)
    assert repository.clear("project/alpha") is False
    repository.record(_entry())
    assert repository.clear("project/alpha") is True
    assert repository.load("project/alpha") == ()


def test_cross_project_history_is_rejected(tmp_path: Path) -> None:
    repository = ExportHistoryRepository(tmp_path)
    path = repository.record(_entry("alpha"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["entries"][0]["project_id"] = "beta"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="another project"):
        repository.load("alpha")


def test_streamlit_panel_records_history_and_exposes_reset_controls() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "ExportHistoryRepository" in source
    assert "history_repository.record(" in source
    assert "Сбросить настройки" in source
    assert "Очистить историю" in source
