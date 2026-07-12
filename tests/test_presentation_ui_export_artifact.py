from __future__ import annotations

from zipfile import ZipFile
from io import BytesIO

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_ui import build_presentation_export_ui_state, build_ui_export_artifact


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


def _model():
    payload = build_hydrocarbon_report_payload(
        _sample_frame(),
        source_label="well.las",
        project_label="Default",
        depth_label="2148.2–2156.0 м",
        include_plot=True,
    )
    assert payload.presentation_model is not None
    return payload.presentation_model


def test_ui_export_artifact_returns_download_ready_pdf(tmp_path) -> None:
    state = build_presentation_export_ui_state(
        profile="engineering",
        export_format="pdf",
        output_dir=tmp_path,
        base_name_parts=("Well A",),
    )

    artifact = build_ui_export_artifact(_model(), state)

    assert artifact.file_name == "Well_A.pdf"
    assert artifact.mime_type == "application/pdf"
    assert artifact.content.startswith(b"%PDF")


def test_ui_export_artifact_returns_bundle_zip(tmp_path) -> None:
    state = build_presentation_export_ui_state(
        profile="expert",
        export_format="bundle",
        output_dir=tmp_path,
        base_name_parts=("Well A", "bundle"),
    )

    artifact = build_ui_export_artifact(_model(), state)

    assert artifact.file_name == "Well_A_bundle.zip"
    assert artifact.mime_type == "application/zip"
    with ZipFile(BytesIO(artifact.content)) as archive:
        names = set(archive.namelist())
    assert "Well_A_bundle.pdf" in names
    assert "Well_A_bundle.docx" in names
    assert "Well_A_bundle.pdf.manifest.json" in names
    assert "Well_A_bundle.docx.manifest.json" in names
