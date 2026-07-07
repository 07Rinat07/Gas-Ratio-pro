from __future__ import annotations

import pytest

from las_editor.las_header_designer import (
    HeaderDesignerUpdate,
    apply_header_designer_updates,
    build_las_header_designer_preview,
    build_las_header_designer_session,
    extract_ascii_section,
    finalize_las_header_designer_update,
    header_designer_issue_rows,
    header_designer_required_field_rows,
    header_designer_section_rows,
    header_designer_well_field_rows,
    parse_las_header_cards,
)


SOURCE_LAS = """~Version
VERS. 2.0 : version
WRAP. NO : wrap
~Well
STRT.M 500 : start
STOP.M 501 : stop
STEP.M 0.5 : step
NULL. -999.25 : null
WELL. OLD_WELL : well
FLD. OLD_FIELD : field
~Curve
DEPT.M : Depth
GR.API : Gamma ray
TGAS.PPM : Total gas
~Parameter
RUN. 1 : Run number
~ASCII
500 80 10
500.5 82 12
501 84 14
"""


def test_header_designer_parses_sections_and_builds_ui_rows():
    cards = parse_las_header_cards(SOURCE_LAS)
    session = build_las_header_designer_session(las_text=SOURCE_LAS, source_object_id="las:old")

    assert {card.mnemonic for card in cards} >= {"VERS", "WRAP", "STRT", "STOP", "STEP", "NULL", "WELL", "DEPT", "GR"}
    assert any(row["section"] == "Well" and row["card_count"] >= 5 for row in header_designer_section_rows(session))
    assert any(row["mnemonic"] == "STRT" and row["present"] is True for row in header_designer_required_field_rows(session))
    assert any(row["mnemonic"] == "UWI" for row in header_designer_well_field_rows(session))


def test_header_designer_updates_header_only_and_preserves_ascii_values():
    session = build_las_header_designer_session(las_text=SOURCE_LAS, source_object_id="las:old")
    updated = apply_header_designer_updates(
        session,
        [
            HeaderDesignerUpdate("Well", "WELL", "value", "NEW_WELL"),
            HeaderDesignerUpdate("Well", "UWI", "value", "UWI-001"),
            {"section": "Version", "mnemonic": "VERS", "field": "value", "value": "3.0"},
        ],
    )
    preview = build_las_header_designer_preview(updated)
    final = finalize_las_header_designer_update(updated, original_las_text=SOURCE_LAS, filename="old.las")

    assert preview.can_finalize is True
    assert "WELL. NEW_WELL" in preview.header_text
    assert "UWI. UWI-001" in preview.header_text
    assert final.filename.endswith(".las")
    assert "~ASCII\n500 80 10\n500.5 82 12\n501 84 14\n" in final.las_text
    assert extract_ascii_section(final.las_text) == extract_ascii_section(SOURCE_LAS)
    assert final.journal_entry.status.value == "completed"
    assert final.journal_entry.creates_copy is True
    assert final.journal_entry.details["ascii_preserved"] is True


def test_header_designer_reports_validation_errors_before_finalize():
    session = build_las_header_designer_session(las_text=SOURCE_LAS)
    broken = apply_header_designer_updates(session, [HeaderDesignerUpdate("Well", "STEP", "value", "0")])
    preview = build_las_header_designer_preview(broken)
    rows = header_designer_issue_rows(preview.issues)

    assert preview.can_finalize is False
    assert any(row["code"] == "STEP_INVALID" for row in rows)
    with pytest.raises(ValueError):
        finalize_las_header_designer_update(broken, original_las_text=SOURCE_LAS)


def test_header_designer_depth_reversal_is_warning_not_data_change():
    session = build_las_header_designer_session(las_text=SOURCE_LAS)
    reversed_header = apply_header_designer_updates(
        session,
        [
            HeaderDesignerUpdate("Well", "STRT", "value", "501"),
            HeaderDesignerUpdate("Well", "STOP", "value", "500"),
        ],
    )
    preview = build_las_header_designer_preview(reversed_header)
    final = finalize_las_header_designer_update(reversed_header, original_las_text=SOURCE_LAS)

    assert any(issue.code == "DEPTH_RANGE_REVERSED" and issue.severity == "warning" for issue in preview.issues)
    assert final.las_text.split("~ASCII", 1)[1].strip().splitlines()[0] == "500 80 10"
    assert final.las_text.split("~ASCII", 1)[1].strip().splitlines()[-1] == "501 84 14"
