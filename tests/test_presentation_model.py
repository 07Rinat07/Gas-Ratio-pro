from __future__ import annotations

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_model import PresentationMetadata, build_presentation_model


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


def test_hydrocarbon_payload_contains_single_presentation_model() -> None:
    payload = build_hydrocarbon_report_payload(
        _sample_frame(),
        source_label="sample.las",
        project_label="Default",
        depth_label="2148.2–2156.0 м",
        include_plot=True,
    )

    model = payload.presentation_model

    assert model is not None
    assert model.result is payload.result
    assert model.executive_summary is payload.executive_summary
    assert model.interval_cards == payload.interval_cards
    assert model.metadata.source_label == "sample.las"
    assert model.metadata.project_label == "Default"
    assert model.metadata.depth_label == "2148.2–2156.0 м"
    assert model.well_log_plot is not None
    assert model.figures == (model.well_log_plot.figure,)
    assert model.engineer_first_tables
    assert model.expert_tables[-1].title == "Диагностика движка УВ-интервалов"


def test_presentation_metadata_keeps_report_header_engineer_focused() -> None:
    rows = PresentationMetadata(
        source_label="LAS",
        project_label="Main",
        depth_label="1000–1010 м",
        report_profile="engineering",
    ).as_report_rows()

    text = " ".join(label + " " + value for label, value in rows)

    assert "Источник данных LAS" in text
    assert "Интервал анализа 1000–1010 м" in text
    assert "Строк" not in text
    assert "row" not in text.lower()


def test_build_presentation_model_does_not_reinterpret_existing_result() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame())
    model = build_presentation_model(
        result=payload.result,
        source_df=_sample_frame(),
        executive_summary=payload.executive_summary,
        interval_cards=payload.interval_cards,
        engineering_tables=payload.professional_tables[:2],
        technical_tables=payload.tables,
        include_plot=False,
    )

    assert model.result is payload.result
    assert model.intervals == payload.intervals
    assert model.well_log_plot is None
    assert model.figures == ()
