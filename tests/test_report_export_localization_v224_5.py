from reports.report_i18n import localize_text, tr
from reports.presentation_model import PresentationMetadata


def test_metadata_rows_are_localized():
    kk = PresentationMetadata(source_label="LAS", project_label="P", depth_label="1–2 м", report_profile="engineering", locale="kk")
    en = PresentationMetadata(source_label="LAS", project_label="P", depth_label="1–2 m", report_profile="client", locale="en")
    assert kk.as_report_rows()[0][0] == "Деректер көзі"
    assert kk.as_report_rows()[-1][1] == "Инженерлік"
    assert en.as_report_rows()[0][0] == "Data source"
    assert en.as_report_rows()[-1][1] == "Client"


def test_report_titles_and_fluids_are_localized():
    assert tr("kk", "report.overview") == "Ұңғыманың шолу планшеті"
    assert tr("en", "report.conclusion") == "Conclusions and limitations"
    assert "Oil interval" in localize_text("Нефтяной интервал", "en")
    assert "Мұнай аралығы" in localize_text("Нефтяной интервал", "kk")
