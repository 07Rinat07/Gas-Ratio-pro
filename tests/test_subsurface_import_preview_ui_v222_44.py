from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py").read_text(encoding="utf-8")


def test_data_workspace_wires_bounded_subsurface_preview():
    assert "def _render_subsurface_import_preview" in SOURCE
    assert 'type=["dlis", "lis", "sgy", "segy"]' in SOURCE
    assert "build_import_preview" in SOURCE
    assert "scan_segy_trace_headers" in SOURCE
    assert "coordinate_scalar_byte=scalar_byte" in SOURCE
    assert "_render_subsurface_import_preview(logger, active_project)" in SOURCE
