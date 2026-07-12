from types import SimpleNamespace
from pathlib import Path

from app.streamlit_app import _selected_interval_print_range


def test_selected_interval_print_range_uses_interval_bounds():
    interval = SimpleNamespace(top=1496.6, base=1485.6)
    assert _selected_interval_print_range(interval, (47.0, 2016.2)) == (1485.6, 1496.6)


def test_selected_interval_print_range_falls_back_safely():
    interval = SimpleNamespace(top="bad", base=None)
    assert _selected_interval_print_range(interval, (2016.2, 47.0)) == (47.0, 2016.2)


def test_data_workspace_pixler_and_ternary_use_shared_interval_contract():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert '"selected_reservoir_interval_id"' in source
    assert '"Выбранный пласт для Pixler и ternary"' in source
    assert "pixler_interval_frame = calculated_df.loc[" in source
    assert "build_pixler_palette(" in source
    assert "build_ternary_palette(" in source


def test_professional_export_defaults_to_selected_reservoir():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'print_mode_options.insert(0, "Выбранный пласт")' in source
    assert '_selected_interval_print_range(' in source
    assert 'PDF и DOCX формируются только по его фактическим границам.' in source
