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
    from app.streamlit_app import _print_center_container
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR

    class FakeStreamlit:
        def __init__(self):
            self.markdown_calls = []
            self.popover_calls = []

        def markdown(self, body, **kwargs):
            self.markdown_calls.append((body, kwargs))

        def popover(self, label, **kwargs):
            self.popover_calls.append((label, kwargs))
            return {"kind": "popover", "label": label}

    fake = FakeStreamlit()
    container = _print_center_container(fake)

    assert container == {
        "kind": "popover",
        "label": PROFESSIONAL_EXPORT_BEHAVIOR.panel_label,
    }
    assert fake.popover_calls == [
        (
            PROFESSIONAL_EXPORT_BEHAVIOR.panel_label,
            {"help": PROFESSIONAL_EXPORT_BEHAVIOR.panel_help},
        )
    ]
    assert PROFESSIONAL_EXPORT_BEHAVIOR.expanded_default is False
    assert any("stPopover" in body for body, _ in fake.markdown_calls)
