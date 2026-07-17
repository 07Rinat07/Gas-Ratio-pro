from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def _professional_export_source() -> str:
    source = APP_PATH.read_text(encoding="utf-8")
    start = source.index("def _render_professional_export_panel(")
    end = source.index("\ndef ", start + 5)
    return source[start:end]


def test_print_range_is_resolved_before_preview_signature() -> None:
    source = _professional_export_source()

    range_assignment = source.index(
        "print_top, print_bottom = full_print_min, full_print_max"
    )
    signature_build = source.index(
        "preview_counts_signature = build_report_document_counts_signature("
    )

    assert range_assignment < signature_build


def test_report_designer_mode_does_not_mix_session_state_and_index() -> None:
    source = _professional_export_source()

    assert 'mode_widget_kwargs = {"index": 2} if mode_widget_key not in export_state else {}' in source
    assert "**mode_widget_kwargs" in source


def test_export_form_contains_submit_button() -> None:
    source = _professional_export_source()

    form_start = source.index('with st.form(key=f"presentation_export_form_')
    submit = source.index("st.form_submit_button(", form_start)

    assert submit > form_start


def test_state_controller_is_initialized_before_plot_selection_read() -> None:
    source = _professional_export_source()

    initialization = source.index("state_controller = _application_state_controller()")
    selection_read = source.index("selected_plot_point = state_controller.get_value(")

    assert initialization < selection_read
    assert source.count("state_controller = _application_state_controller()") == 1
    assert source.count("export_state = state_controller.state") == 1
