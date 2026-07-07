from __future__ import annotations

import pytest

from las_editor.header_editor import (
    add_header_card,
    build_default_header_cards,
    build_header_manifest,
    delete_header_card,
    header_editor_table_rows,
    render_las_header,
    update_header_card,
    validate_header_cards,
)


def test_default_header_cards_include_required_las_sections_and_items():
    cards = build_default_header_cards(
        well_name="B3-Well",
        start_depth=1000,
        stop_depth=1001,
        step=0.5,
        curves=[{"mnemonic": "GR", "unit": "API", "description": "Gamma ray"}],
        parameters={"RUN": "MAIN"},
    )
    manifest = build_header_manifest(cards)

    assert manifest["Version"]["VERS"]["value"] == "2.0"
    assert manifest["Well"]["WELL"]["value"] == "B3-Well"
    assert manifest["Well"]["STRT"]["protected"] is True
    assert manifest["Curve"]["DEPT"]["protected"] is True
    assert manifest["Curve"]["GR"]["unit"] == "API"
    assert not [issue for issue in validate_header_cards(cards) if issue.severity == "error"]


def test_header_editor_updates_metadata_without_las_ascii_data():
    cards = build_default_header_cards(well_name="Well", start_depth=1, stop_depth=2, step=0.5)
    result = update_header_card(cards, "Well", "WELL", field="value", value="Updated Well")

    assert result.manifest["Well"]["WELL"]["value"] == "Updated Well"
    assert result.history[-1].action == "update_header_card"
    assert "Header-only operation completed safely." in result.diagnostics


def test_header_editor_adds_and_deletes_non_protected_cards():
    cards = build_default_header_cards(well_name="Well", start_depth=1, stop_depth=2, step=0.5)
    added = add_header_card(cards, {"section": "Parameter", "mnemonic": "MUD", "value": "WBM", "description": "Mud type"})

    assert added.manifest["Parameter"]["MUD"]["value"] == "WBM"
    assert added.history[-1].action == "add_header_card"

    deleted = delete_header_card(added.cards, "Parameter", "MUD", history=added.history)
    assert "MUD" not in deleted.manifest["Parameter"]
    assert deleted.history[-1].action == "delete_header_card"


def test_header_editor_protects_mandatory_cards_from_deletion():
    cards = build_default_header_cards(well_name="Well", start_depth=1, stop_depth=2, step=0.5)

    with pytest.raises(ValueError):
        delete_header_card(cards, "Well", "STRT")
    with pytest.raises(ValueError):
        delete_header_card(cards, "Curve", "DEPT")


def test_header_editor_table_and_render_are_ui_ready():
    cards = build_default_header_cards(well_name="Well", start_depth=1, stop_depth=2, step=0.5, curves=["GR"])
    rows = header_editor_table_rows(cards)
    text = render_las_header(cards)

    assert rows[0]["section"] == "Version"
    assert any(row["mnemonic"] == "GR" for row in rows)
    assert "~Version" in text
    assert "~Well" in text
    assert "~Curve" in text
    assert "GR." in text


def test_header_validator_reports_invalid_step():
    cards = build_default_header_cards(well_name="Well", start_depth=1, stop_depth=2, step=0.5)
    result = update_header_card(cards, "Well", "STEP", field="value", value="0")
    codes = {issue.code for issue in result.issues}

    assert "STEP_INVALID" in codes
