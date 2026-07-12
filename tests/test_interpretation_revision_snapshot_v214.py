from __future__ import annotations

import ast
from pathlib import Path

from core.presentation_runtime import RevisionController, RevisionSnapshot


def test_revision_snapshot_exposes_calculation_field() -> None:
    controller = RevisionController(RevisionSnapshot())
    snapshot = controller.bump_calculation()
    assert snapshot.calculation == 1


def test_streamlit_app_does_not_reference_removed_calculation_revision_attribute() -> None:
    source_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    invalid = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "calculation_revision"
        and isinstance(node.value, ast.Name)
        and node.value.id == "snapshot"
    ]
    assert invalid == []


def test_active_calculation_contract_uses_calculation_revision_value() -> None:
    source_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    source = source_path.read_text(encoding="utf-8")
    assert '"calculation_revision": int(snapshot.calculation)' in source
    assert 'int(snapshot.calculation),' in source
