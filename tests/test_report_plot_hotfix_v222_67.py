from __future__ import annotations

from pathlib import Path

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks, build_depth_ratio_tracks
from reports.well_log_plot import WellLogPlotConfig, build_professional_well_log_plot


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "depth": [1000.0, 1001.0, 1002.0],
        "c1": [1.0, 2.0, 3.0], "c2": [0.5, 1.0, 1.5], "c3": [0.2, 0.3, 0.4],
        "ic4": [0.1, 0.2, 0.3], "nc4": [0.1, 0.2, 0.3],
        "ic5": [0.05, 0.1, 0.15], "nc5": [0.05, 0.1, 0.15],
        "wh": [10.0, 20.0, 30.0], "bh": [5.0, 6.0, 7.0], "ch": [2.0, 3.0, 4.0],
    })


def test_export_panel_does_not_pass_document_locale_to_constructor() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "object.__setattr__(preview_design, \"document_locale\"" in source
    assert "object.__setattr__(report_design, \"document_locale\"" in source


def test_depth_gas_chart_contains_total_and_statistics() -> None:
    figure = build_depth_gas_tracks(_frame())
    names = {str(trace.name) for trace in figure.data}
    assert "Σ C1–C5" in names
    stats = list((figure.layout.meta or {}).get("gas_ratio_statistics", []))
    assert any(row["label"] == "Σ C1–C5" for row in stats)


def test_wh_bh_ch_are_present_and_statistical() -> None:
    figure = build_depth_ratio_tracks(_frame())
    names = {str(trace.name) for trace in figure.data}
    assert {"Wh", "Bh", "Ch"}.issubset(names)
    stats = list((figure.layout.meta or {}).get("gas_ratio_statistics", []))
    assert {"Wh", "Bh", "Ch"}.issubset({row["label"] for row in stats})


def test_print_plot_contains_statistics_and_selected_point() -> None:
    frame = _frame()
    frame.attrs["report_plot_selection"] = {"depth": 1001.0, "x": 2.0}
    result = build_professional_well_log_plot(
        frame,
        config=WellLogPlotConfig(track_columns=("c1", "c2", "c3", "wh", "bh", "ch"), layout_profile="print"),
    )
    payload = result.figure.layout.meta["gas_ratio_report_legend"]
    assert {"Wh", "Bh", "Ch"}.issubset({row["label"] for row in payload["statistics"]})
    assert any("Выбрано:" in str(annotation.text) for annotation in result.figure.layout.annotations)
