from pathlib import Path


def test_interpretation_workspace_loads_palette_in_local_scope():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    start = source.index("def _render_interpretation_graphs_tab")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]

    assert "palette_config = load_palette_config()" in body
    assert "interpretation_palette_config_load_failed" in body
    assert "pixler_zones=palette_config.pixler_zones" in body
    assert "ternary_regions=palette_config.ternary_regions" in body
