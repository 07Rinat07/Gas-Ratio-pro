from __future__ import annotations

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_html import PresentationHtmlOptions, build_presentation_html_report, select_presentation_tables


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [2148.2, 2149.0, 2155.0, 2156.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь", "Нефтяная залежь"],
            "c1": [0.1, 0.2, 0.15, 0.12],
            "wh": [6.0, 7.0, 25.0, 26.0],
            "bh": [45.0, 44.0, 10.0, 11.0],
            "c1_c2": [80.0, 82.0, 6.0, 6.5],
            "oil_indicator": [0.04, 0.05, 0.2, 0.22],
            "lithology": ["Sandstone", "Sandstone", "Sandstone", "Sandstone"],
        }
    )


def test_engineering_presentation_html_uses_engineer_first_profile() -> None:
    payload = build_hydrocarbon_report_payload(
        _sample_frame(),
        source_label="sample.las",
        project_label="Default",
        depth_label="2148.2–2156.0 м",
        include_plot=True,
    )
    assert payload.presentation_model is not None

    rendered = build_presentation_html_report(payload.presentation_model)
    html = rendered.content.decode("utf-8")

    assert rendered.profile == "engineering"
    assert rendered.figure_count == 1
    assert "Инженерная сводка перспективных интервалов" in html
    assert "Реестр интерпретированных УВ-интервалов" in html
    assert "Профессиональный планшет интерпретации" in html
    assert "Диагностика движка УВ-интервалов" not in html
    assert "Technical row" not in html
    assert "Строк" not in " ".join(payload.presentation_model.metadata.as_report_rows()[0])


def test_expert_presentation_html_can_include_technical_appendix_tables() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame(), report_profile="expert")
    assert payload.presentation_model is not None

    rendered = build_presentation_html_report(
        payload.presentation_model,
        options=PresentationHtmlOptions(include_figures=False, include_technical_appendix=True),
    )
    html = rendered.content.decode("utf-8")

    assert rendered.profile == "engineering"
    assert rendered.figure_count == 0
    assert "Диагностика движка УВ-интервалов" in html
    assert "Сводка выявленных УВ-интервалов" in html


def test_select_presentation_tables_does_not_rebuild_or_duplicate_tables() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame())
    assert payload.presentation_model is not None

    engineering = select_presentation_tables(payload.presentation_model, include_technical_appendix=False)
    expert = select_presentation_tables(payload.presentation_model, include_technical_appendix=True)

    assert engineering == payload.presentation_model.engineer_first_tables
    assert expert == payload.presentation_model.expert_tables
    assert len(expert) > len(engineering)
