from pathlib import Path


def _render_settings_block() -> str:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    start = source.index("    render_settings = interpretation_graph_settings_from_dict")
    end = source.index("    # Plotly construction is expensive", start)
    return source[start:end]


def test_applied_full_interval_resolves_to_concrete_depth_range() -> None:
    block = _render_settings_block()
    assert "depth_range = _effective_depth_range(filtered_df, None)" in block
    assert "depth_range = None" not in block


def test_applied_manual_interval_is_normalized_before_filtering() -> None:
    block = _render_settings_block()
    assert "depth_range = _effective_depth_range(calculated_df, render_settings.depth_range)" in block
    assert "_filter_by_depth_range(calculated_df, depth_range[0], depth_range[1])" in block


def test_export_metadata_uses_safe_effective_depth_range() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert source.count('"depth_range": _effective_depth_range(filtered_df, depth_range)') >= 1
