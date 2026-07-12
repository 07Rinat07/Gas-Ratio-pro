from __future__ import annotations

from pathlib import Path

from core.presentation_runtime import RevisionController, RevisionSnapshot


def test_revision_snapshot_exposes_canonical_and_compatibility_fields() -> None:
    controller = RevisionController(RevisionSnapshot())
    snapshot = controller.bump_calculation()

    assert snapshot.calculation == 1
    assert snapshot.calculation_revision == 1
    assert snapshot.data_revision == snapshot.data
    assert snapshot.presentation_revision == snapshot.presentation
    assert snapshot.export_revision == snapshot.export


def test_active_calculation_contract_uses_compatible_revision_property() -> None:
    source_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    source = source_path.read_text(encoding="utf-8")

    assert '"calculation_revision": int(snapshot.calculation_revision)' in source
    assert 'int(snapshot.calculation_revision),' in source
