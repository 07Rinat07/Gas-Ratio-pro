from __future__ import annotations

import json

import pandas as pd
import pytest

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_export import (
    PresentationExportOptions,
    export_presentation_html_package,
    safe_export_basename,
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


def test_safe_export_basename_blocks_path_like_names() -> None:
    assert safe_export_basename("../well A/print report") == "well_A_print_report"
    assert safe_export_basename("   ") == "gas-ratio-professional-report"


def test_export_presentation_html_package_writes_html_and_manifest(tmp_path) -> None:
    payload = build_hydrocarbon_report_payload(
        _sample_frame(),
        source_label="well.las",
        project_label="Default",
        depth_label="2148.2–2156.0 м",
        include_plot=True,
    )
    assert payload.presentation_model is not None

    result = export_presentation_html_package(
        payload.presentation_model,
        options=PresentationExportOptions(output_dir=tmp_path, base_name="Well A engineering report"),
    )

    assert result.html_path.exists()
    assert result.manifest_path.exists()
    assert result.profile == "engineering"
    assert result.figure_count == 1

    html = result.html_path.read_text(encoding="utf-8")
    assert "Краткое инженерное заключение" in html
    assert "Диагностика движка УВ-интервалов" not in html

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "gas-ratio-pro/presentation/export/v1"
    assert manifest["profile"] == "engineering"
    assert manifest["metadata"]["source_label"] == "well.las"
    assert manifest["html_file"] == result.html_path.name


def test_export_presentation_html_package_respects_overwrite_flag(tmp_path) -> None:
    payload = build_hydrocarbon_report_payload(_sample_frame())
    assert payload.presentation_model is not None

    options = PresentationExportOptions(output_dir=tmp_path, base_name="report", overwrite=False)
    export_presentation_html_package(payload.presentation_model, options=options)

    with pytest.raises(FileExistsError):
        export_presentation_html_package(payload.presentation_model, options=options)
