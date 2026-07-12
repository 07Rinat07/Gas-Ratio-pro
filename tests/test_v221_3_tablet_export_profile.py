from __future__ import annotations

import pandas as pd

from palettes.well_log_tablet import (
    InterpretationZone,
    ReservoirIntervalOverlay,
    TabletTrackConfig,
    build_well_log_tablet,
)
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_model import PresentationMetadata


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [1000.0, 1000.5, 1001.0, 1001.5],
            "c1": [0.1, 0.4, 0.2, 0.7],
            "c2": [0.03, 0.08, 0.05, 0.1],
            "c3": [0.01, 0.03, 0.02, 0.04],
            "ic4": [0.005, 0.008, 0.007, 0.009],
            "nc4": [0.004, 0.007, 0.006, 0.008],
            "ic5": [0.002, 0.004, 0.003, 0.005],
            "nc5": [0.001, 0.003, 0.002, 0.004],
        }
    )


def test_tablet_has_readable_track_lines_and_separated_engineering_titles() -> None:
    fig = build_well_log_tablet(
        _frame(),
        [TabletTrackConfig(column="c1"), TabletTrackConfig(column="c2")],
        reservoir_intervals=[
            ReservoirIntervalOverlay(
                interval_id="HC-001",
                top_depth=1000.5,
                bottom_depth=1001.5,
                thickness=1.0,
                fluid_type="oil",
                confidence_score=90,
            )
        ],
        zones=[InterpretationZone(top_depth=1000.4, bottom_depth=1001.6, label="УВ")],
        selected_depth=1001.0,
    )
    visible_lines = [trace for trace in fig.data if getattr(trace, "name", None) in {"c1", "c2"}]
    assert visible_lines
    assert all(float(trace.line.width) >= 2.0 for trace in visible_lines)
    titles = [str(a.text) for a in fig.layout.annotations[:5]]
    assert "Тип<br>пласта" in titles
    assert "Достовер-<br>ность" in titles
    assert all(int(a.font.size) <= 11 for a in fig.layout.annotations[:5])
    interval_bands = [shape for shape in fig.layout.shapes if shape.type == "rect" and shape.xref == "paper"]
    assert any(float(shape.opacity) >= 0.1 for shape in interval_bands)


def test_client_profile_is_preserved_in_presentation_model() -> None:
    payload = build_hydrocarbon_report_payload(
        _frame(),
        source_label="LAS",
        project_label="Проект",
        depth_label="1000–1001.5 м",
        report_profile="client",
        include_plot=False,
    )
    assert payload.presentation_model is not None
    assert payload.presentation_model.metadata.report_profile == "client"
    rows = dict(payload.presentation_model.metadata.as_report_rows())
    assert rows["Профиль отчета"] == "Для заказчика"


def test_presentation_metadata_profile_labels() -> None:
    assert dict(PresentationMetadata(report_profile="client").as_report_rows())["Профиль отчета"] == "Для заказчика"
    assert dict(PresentationMetadata(report_profile="engineering").as_report_rows())["Профиль отчета"] == "Инженерный"
