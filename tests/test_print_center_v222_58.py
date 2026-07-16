from reports.print_center import PrintCenterSession, default_report_copy, document_locale_options


def test_print_center_supports_three_document_languages():
    assert [code for code, _ in document_locale_options()] == ["ru", "kk", "en"]


def test_report_copy_is_localized_and_not_mixed():
    assert "Инженерное" in default_report_copy("ru")["subtitle"]
    assert "инженерлік" in default_report_copy("kk")["subtitle"].lower()
    assert "Engineering" in default_report_copy("en")["subtitle"]


def test_print_center_session_is_json_safe():
    payload = PrintCenterSession(project_id="default", document_locale="kk").to_dict()
    assert payload["document_locale"] == "kk"
    assert payload["project_id"] == "default"


def test_workbench_uses_compact_print_center_trigger():
    source = open("app/streamlit_app.py", encoding="utf-8").read()
    assert "_print_center_container(st)" in source
    assert "🖨 Печать и экспорт" in source
    assert 'with st.expander("Отчёт и печать"' not in source
