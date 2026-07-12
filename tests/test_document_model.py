from __future__ import annotations

import pandas as pd

from reports.document_model import (
    DocumentNotice,
    DocumentPlot,
    DocumentTable,
    build_engineering_document,
    select_document_tables,
)
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_html import build_presentation_html_report


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


def test_document_model_is_renderer_neutral_single_source() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=True)
    assert payload.presentation_model is not None

    document = build_engineering_document(payload.presentation_model, include_figures=True)

    assert document.schema == "gas-ratio-pro/document/model/v1"
    assert document.metadata.profile == "engineering"
    assert "Инженерная сводка перспективных интервалов" in document.table_titles
    assert document.plot_count == 1
    assert any(isinstance(block, DocumentTable) for section in document.sections for block in section.blocks)
    assert any(isinstance(block, DocumentPlot) for section in document.sections for block in section.blocks)
    assert any(isinstance(block, DocumentNotice) for section in document.sections for block in section.blocks)


def test_document_table_selection_matches_presentation_model_without_rebuild() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame())
    assert payload.presentation_model is not None

    client = select_document_tables(payload.presentation_model, include_technical_appendix=False)
    engineering = select_document_tables(payload.presentation_model, include_technical_appendix=True)

    assert len(client) <= 5
    assert tuple(table.title for table in engineering) == tuple(table.title for table in payload.presentation_model.expert_tables)
    assert len(engineering) >= len(client)


def test_html_renderer_consumes_document_model_contract() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=True)
    assert payload.presentation_model is not None

    document = build_engineering_document(payload.presentation_model, include_figures=True, include_technical_appendix=False)
    rendered = build_presentation_html_report(payload.presentation_model)

    assert rendered.table_titles == document.table_titles
    assert rendered.figure_count == document.plot_count
    assert rendered.profile == document.metadata.profile
    html = rendered.content.decode("utf-8")
    assert "Ограничения интерпретации" in html
    assert "Диагностика движка УВ-интервалов" not in html
