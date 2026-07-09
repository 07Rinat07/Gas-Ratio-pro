from __future__ import annotations

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_freeze import (
    DOCUMENT_MODEL_SCHEMA,
    PRESENTATION_LAYER_FREEZE_VERSION,
    PRESENTATION_MODEL_SCHEMA,
    build_presentation_freeze_status,
)


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


def test_presentation_layer_freeze_gate_passes_for_engineering_profile() -> None:
    payload = build_hydrocarbon_report_payload(
        _sample_frame(),
        source_label="well.las",
        project_label="Default",
        depth_label="2148.2–2156.0 м",
        include_plot=True,
    )
    assert payload.presentation_model is not None

    status = build_presentation_freeze_status(payload.presentation_model)

    assert status.version == PRESENTATION_LAYER_FREEZE_VERSION
    assert status.frozen is True
    assert status.failed_checks == ()
    assert status.presentation_schema == PRESENTATION_MODEL_SCHEMA
    assert status.document_schema == DOCUMENT_MODEL_SCHEMA
    status.require_frozen()


def test_presentation_layer_freeze_gate_detects_schema_drift() -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame(), include_plot=False)
    assert payload.presentation_model is not None
    drifted_model = payload.presentation_model.__class__(
        result=payload.presentation_model.result,
        executive_summary=payload.presentation_model.executive_summary,
        interval_cards=payload.presentation_model.interval_cards,
        engineering_tables=payload.presentation_model.engineering_tables,
        technical_tables=payload.presentation_model.technical_tables,
        well_log_plot=payload.presentation_model.well_log_plot,
        metadata=payload.presentation_model.metadata,
        schema="gas-ratio-pro/presentation/model/v999",
    )

    status = build_presentation_freeze_status(drifted_model, include_figures=False)

    assert status.frozen is False
    assert any(check.code == "presentation_schema_v1" for check in status.failed_checks)
