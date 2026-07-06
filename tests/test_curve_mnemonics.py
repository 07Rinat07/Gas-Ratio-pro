from __future__ import annotations

from las_editor.curve_mnemonics import (
    curve_mnemonic_table_rows,
    lookup_curve_mnemonic,
    mnemonic_reference_manifest,
    mnemonic_summary_rows,
)


def test_lookup_dictionary_mnemonic():
    record = lookup_curve_mnemonic("GR")

    assert record.canonical == "GR"
    assert record.label == "Gamma ray"
    assert record.group == "gamma"
    assert record.category == "petrophysics"
    assert record.unit == "api"
    assert record.match_type == "dictionary"


def test_lookup_alias_mnemonic():
    record = lookup_curve_mnemonic("TOTAL_GAS")

    assert record.canonical == "TGAS"
    assert record.group == "total_gas"
    assert record.match_type == "alias"


def test_unknown_mnemonic_gets_safe_suggestion():
    record = lookup_curve_mnemonic("UNKNOWN_CURVE")

    assert record.canonical == "UNKNOWN_CURVE"
    assert record.match_type == "suggested"
    assert "проверьте" in record.recommendation.lower()


def test_mnemonic_table_and_summary_rows():
    rows = curve_mnemonic_table_rows(["DEPT", "TOTAL_GAS", "UNKNOWN_CURVE"])

    assert rows[0]["canonical"] == "DEPT"
    assert rows[1]["canonical"] == "TGAS"
    assert rows[2]["match_type"] == "suggested"

    summary = mnemonic_summary_rows(["DEPT", "TOTAL_GAS", "UNKNOWN_CURVE"])
    values = {row["metric"]: row["value"] for row in summary}
    assert values["Всего кривых"] == "3"
    assert values["Найдено по словарю"] == "1"
    assert values["Найдено по alias"] == "1"
    assert values["Требуют проверки"] == "1"


def test_reference_manifest_contains_mnemonics():
    manifest = mnemonic_reference_manifest(["GR"], references={"source": "test"})

    assert manifest["source"] == "test"
    assert manifest["curve_mnemonics"]["GR"]["canonical"] == "GR"
