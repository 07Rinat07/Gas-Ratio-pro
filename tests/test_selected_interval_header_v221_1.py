from pathlib import Path


def test_selected_interval_header_is_defined_before_workspace_calls() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert source.count("def _render_selected_interval_header(") == 1
    assert source.count("    _render_selected_interval_header(\n") >= 2


def test_selected_interval_header_handles_empty_selection() -> None:
    import app.streamlit_app as module

    messages: list[str] = []
    original_info = module.st.info
    module.st.info = messages.append
    try:
        module._render_selected_interval_header(None, "")
    finally:
        module.st.info = original_info

    assert messages == ["Инженерный интервал не выбран."]
