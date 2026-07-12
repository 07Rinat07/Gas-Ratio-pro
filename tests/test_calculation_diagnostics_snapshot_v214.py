from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.calculation_diagnostics import (
    build_calculation_diagnostics_report,
    calculation_diagnostics_from_dict,
    calculation_diagnostics_to_dict,
)
from core.workbench_ui_layout import WorkbenchUILayoutContract, build_workbench_ui_layout
from projects.calculations import (
    check_project_calculation_integrity,
    read_project_calculation_diagnostics,
    save_project_calculation,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "depth": [1.0, 2.0, 3.0],
        "c1": [10.0, 11.0, 12.0],
        "c2": [2.0, 0.0, 3.0],
        "c3": [1.0, None, 2.0],
        "ic4": [0.2, 0.3, 0.4],
        "nc4": [0.2, 0.3, 0.4],
        "ic5": [0.1, 0.1, 0.1],
        "nc5": [0.1, 0.1, 0.1],
        "wh": [30.0, None, 31.0],
        "bh": [4.0, None, 4.2],
        "ch": [0.6, None, 0.5],
        "bar2": [5.0, None, 4.0],
        "oil_indicator": [0.16, None, 0.25],
        "inverse_oil_indicator": [6.25, None, 4.0],
    })


def test_workbench_layout_contract_accepts_properties_actions() -> None:
    layout = build_workbench_ui_layout({
        "ui_providers": {
            "property_actions": ({"id": "open", "title": "Open"},),
            "property_action_result": {"success": True},
            "show_technical_properties": True,
        }
    })
    assert isinstance(layout, WorkbenchUILayoutContract)
    assert layout.property_actions[0]["id"] == "open"
    assert layout.property_action_result["success"] is True
    assert layout.show_technical_properties is True
    assert layout.to_dict()["property_actions"][0]["id"] == "open"


def test_diagnostics_snapshot_roundtrip() -> None:
    report = build_calculation_diagnostics_report(_frame(), ch_mode="A")
    payload = calculation_diagnostics_to_dict(report)
    restored = calculation_diagnostics_from_dict(payload)
    assert restored.total_rows == report.total_rows
    assert len(restored.columns) == len(report.columns)
    assert len(restored.formulas) == len(report.formulas)
    assert not restored.problematic_rows.empty


def test_calculation_saves_and_validates_diagnostics_snapshot(tmp_path: Path) -> None:
    frame = _frame()
    payload = calculation_diagnostics_to_dict(build_calculation_diagnostics_report(frame, ch_mode="A"))
    record = save_project_calculation(
        frame,
        root=tmp_path,
        project_id="default",
        source_label="diagnostic test",
        diagnostics=payload,
    )
    assert record.files["diagnostics"] == "diagnostics.json"
    stored = read_project_calculation_diagnostics(tmp_path, "default", record.id)
    assert stored is not None
    assert stored["total_rows"] == len(frame)
    assert check_project_calculation_integrity(tmp_path, "default", record.id).ok


def test_legacy_calculation_without_diagnostics_remains_valid(tmp_path: Path) -> None:
    record = save_project_calculation(_frame(), root=tmp_path, project_id="default", source_label="legacy")
    assert read_project_calculation_diagnostics(tmp_path, "default", record.id) is None
    assert check_project_calculation_integrity(tmp_path, "default", record.id).ok
