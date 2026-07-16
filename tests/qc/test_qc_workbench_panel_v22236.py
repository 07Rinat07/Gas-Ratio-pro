from pathlib import Path


def test_las_editor_contains_production_qc_panel_contract():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "def _render_las_qc_panel(" in source
    assert "qc.filter_report(" in source
    assert "qc.persist_report(" in source
    assert "qc.export_and_register(" in source
    assert "qc.panel.filter.severity" in source
    assert "qc.panel.filter.code" in source
    assert "curve_statistics" in source
