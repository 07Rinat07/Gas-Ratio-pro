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


def test_history_filter_matches_search_format_and_profile() -> None:
    from reports.export_history import ExportHistoryFilter, filter_export_history

    entries = (
        _entry(index=1),
        ExportHistoryEntry(
            project_id="project/alpha",
            file_name="summary.docx",
            format_id="docx",
            format_label="DOCX",
            profile_id="summary",
            depth_top=100.0,
            depth_bottom=200.0,
            size_bytes=200,
        ),
    )

    assert [item.file_name for item in filter_export_history(entries, ExportHistoryFilter(search="SUMMARY"))] == ["summary.docx"]
    assert [item.file_name for item in filter_export_history(entries, ExportHistoryFilter(format_id="PDF"))] == ["report_1.pdf"]
    assert [item.file_name for item in filter_export_history(entries, ExportHistoryFilter(profile_id="summary"))] == ["summary.docx"]


def test_streamlit_panel_exposes_history_filters_and_repeat_action() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "filter_export_history(" in source
    assert "Поиск в истории" in source
    assert '"Повторить"' in source
    assert "export_history_repeat_pending_" in source


def test_history_round_trip_preserves_full_report_design(tmp_path: Path) -> None:
    repository = ExportHistoryRepository(tmp_path)
    repository.record(
        ExportHistoryEntry(
            project_id="project/alpha",
            file_name="custom.pdf",
            format_id="pdf",
            format_label="PDF",
            profile_id="engineering",
            depth_top=1500.0,
            depth_bottom=1750.0,
            size_bytes=4096,
            report_mode_id="custom",
            template_id="corporate",
            report_title="Field A Engineering Review",
            sections=("plots", "results"),
            include_technical_appendix=False,
            show_page_chrome=False,
            print_mode="Выбрать отдельно",
        )
    )

    restored = repository.load("project/alpha")[0]
    assert restored.report_mode_id == "custom"
    assert restored.template_id == "corporate"
    assert restored.report_title == "Field A Engineering Review"
    assert restored.sections == ("plots", "results")
    assert restored.include_technical_appendix is False
    assert restored.show_page_chrome is False
    assert restored.repeat_payload()["report_title"] == "Field A Engineering Review"


def test_history_loads_legacy_v1_entries_with_safe_report_defaults(tmp_path: Path) -> None:
    repository = ExportHistoryRepository(tmp_path)
    target = repository.path_for("project/alpha")
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "schema": "gas-ratio-pro/export-history/v1",
                "project_id": "project/alpha",
                "entries": [_entry().to_dict() | {"report": None}],
            }
        ),
        encoding="utf-8",
    )

    restored = repository.load("project/alpha")[0]
    assert restored.report_mode_id == "full_engineering"
    assert restored.template_id == "engineering"
    assert restored.sections == ("plots", "visualizations", "results", "conclusion")


def test_streamlit_repeat_restores_complete_report_configuration() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "history_item.repeat_payload()" in source
    assert 'pending_repeat.get("report_mode_id"' in source
    assert 'pending_repeat.get("template_id"' in source
    assert 'pending_repeat.get("report_title"' in source
    assert 'pending_repeat.get("sections"' in source
    assert "report_mode_id=report_design.mode_id" in source
    assert "template_id=report_design.template_id" in source
