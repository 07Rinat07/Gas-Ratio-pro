from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def test_initial_interpretation_presentation_is_auto_committed() -> None:
    source = APP.read_text(encoding="utf-8")
    assert "interpretation_presentation_auto_committed" in source
    assert "Первичное представление построено автоматически" in source
    assert "Настройте параметры и нажмите `Построить графики и планшет`" not in source


def test_marker_count_widget_has_single_source_of_truth() -> None:
    source = APP.read_text(encoding="utf-8")
    block = source[source.index('marker_count_key = "interpretation_tablet_marker_count"'):]
    block = block[: block.index("markers: list[InterpretationMarker]")]
    assert "\n            value=0," not in block
    assert "st.session_state[marker_count_key] = 0" in block
