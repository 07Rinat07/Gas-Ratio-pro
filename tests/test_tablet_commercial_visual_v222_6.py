from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from palettes.well_log_tablet import TabletTrackConfig, build_well_log_tablet, reservoir_interval_overlays
from reports.export_controller import ExportArtifact, ExportController, ExportRequest
from reports.well_log_plot import WellLogPlotConfig, build_professional_well_log_plot


def _interval(top: float, base: float, fluid: str, confidence: int) -> HydrocarbonInterval:
    return HydrocarbonInterval(
        top=top,
        base=base,
        sample_count=5,
        fluid_type=fluid,
        confidence="high",
        interpretation="test",
        confidence_score=confidence,
    )


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "depth": [1000.0, 1001.0, 1002.0, 1003.0],
        "c1": [1.0, 1.5, 1.2, 2.0],
        "c2": [0.1, 0.3, 0.2, 0.4],
    })


def test_print_tablet_uses_one_depth_title_legend_and_priority_frame() -> None:
    result = build_professional_well_log_plot(
        _frame(),
        (_interval(1000.2, 1001.3, "gas", 70), _interval(1001.5, 1002.8, "oil", 95)),
        config=WellLogPlotConfig(track_columns=("c1", "c2"), auto_crop_to_active_data=False),
    )
    fig = result.figure
    assert fig.layout.showlegend is True
    assert fig.layout.legend.orientation == "h"
    y_titles = [getattr(getattr(fig.layout, key), "title").text for key in fig.layout if str(key).startswith("yaxis")]
    assert y_titles.count("Глубина, м") == 1
    assert any(getattr(shape.line, "color", None) == "#f6c344" for shape in fig.layout.shapes)
    annotation_text = " ".join(str(a.text) for a in fig.layout.annotations)
    assert "1001.5–1002.8 м" in annotation_text


def test_screen_tablet_has_shared_legend_and_priority_interval() -> None:
    intervals = reservoir_interval_overlays((
        _interval(1000.2, 1001.3, "gas", 70),
        _interval(1001.5, 1002.8, "oil", 95),
    ))
    fig = build_well_log_tablet(
        _frame(),
        (TabletTrackConfig("c1", label="C1"), TabletTrackConfig("c2", label="C2")),
        reservoir_intervals=intervals,
        height=700,
    )
    assert fig.layout.showlegend is True
    assert fig.layout.legend.orientation == "h"
    assert any(getattr(shape.line, "color", None) == "#f6c344" for shape in fig.layout.shapes)
    texts = " ".join(str(a.text) for a in fig.layout.annotations)
    assert "1001.5–1002.8 м" in texts


def test_docx_suffix_is_normalized_centrally() -> None:
    request = ExportRequest(
        project_id="p", project_name="P", source_label="LAS", profile_id="engineering",
        format_id="docx", format_label="DOCX", extension="docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        depth_top=1.0, depth_bottom=2.0, source_signature="sig",
        calculation_revision=1, presentation_revision=1, figure_height=800,
    )
    from io import BytesIO
    from zipfile import ZipFile
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    artifact = ExportArtifact(
        content=buffer.getvalue(), file_name="report", mime_type=request.mime_type,
        format_id="docx", format_label="DOCX", profile_id="engineering",
    )
    normalized = ExportController._validate_artifact_contract(artifact, request)
    assert normalized.file_name == "report.docx"
