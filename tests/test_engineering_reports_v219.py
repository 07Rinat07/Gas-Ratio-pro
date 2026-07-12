import pandas as pd

from reports.document_model import build_engineering_document
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_ui import normalize_report_profile, report_profile_options


def _model():
    frame = pd.DataFrame({
        "depth": [2148.2, 2149.0, 2155.0, 2156.0],
        "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь", "Нефтяная залежь"],
        "c1": [0.1, 0.2, 0.15, 0.12], "wh": [6.0, 7.0, 25.0, 26.0],
        "bh": [45.0, 44.0, 10.0, 11.0], "c1_c2": [80.0, 82.0, 6.0, 6.5],
        "oil_indicator": [0.04, 0.05, 0.2, 0.22],
        "lithology": ["Sandstone"] * 4,
    })
    payload = build_hydrocarbon_report_payload(frame, include_plot=True)
    assert payload.presentation_model is not None
    return payload.presentation_model


def test_report_profiles_are_client_and_engineering():
    profiles = report_profile_options()
    assert [p.id for p in profiles] == ["client", "engineering"]
    assert profiles[0].include_technical_appendix is False
    assert profiles[1].include_technical_appendix is True
    assert normalize_report_profile("expert") == "engineering"
    assert normalize_report_profile("заказчик") == "client"


def test_client_report_is_compact_and_has_no_technical_appendix():
    document = build_engineering_document(_model(), include_figures=False, include_technical_appendix=False)
    assert document.metadata.profile == "client"
    assert len(document.metadata.rows) <= 6
    assert all("техническое приложение" not in section.title.lower() for section in document.sections)
    assert any(section.title == "Заключение и ограничения" for section in document.sections)
    assert len(document.table_titles) <= 5


def test_engineering_report_keeps_extended_tables():
    model = _model()
    client = build_engineering_document(model, include_figures=False, include_technical_appendix=False)
    engineering = build_engineering_document(model, include_figures=False, include_technical_appendix=True)
    assert engineering.metadata.profile == "engineering"
    assert len(engineering.table_titles) >= len(client.table_titles)
    assert any(section.title == "Инженерные результаты и расчетные приложения" for section in engineering.sections)
