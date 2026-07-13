from __future__ import annotations

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from reports.presentation_docx import _figure_report_legend as docx_legend
from reports.presentation_pdf import _figure_report_legend as pdf_legend
from reports.well_log_plot import WellLogPlotConfig, build_professional_well_log_plot


def _interval(fluid_type: str = "oil") -> HydrocarbonInterval:
    return HydrocarbonInterval(
        top=2002.8,
        base=2016.2,
        sample_count=68,
        fluid_type=fluid_type,
        confidence="high",
        interpretation="test",
        confidence_score=92,
    )


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [2002.8, 2005.0, 2010.0, 2016.2],
            "c1": [0.02, 0.03, 0.025, 0.04],
            "c2": [0.002, 0.003, 0.0025, 0.004],
            "wh": [18.0, 25.0, 20.0, 30.0],
        }
    )


def test_print_plot_embeds_curve_fluid_and_marker_legend_contract() -> None:
    result = build_professional_well_log_plot(
        _frame(),
        (_interval("oil"),),
        config=WellLogPlotConfig(track_columns=("c1", "c2", "wh")),
    )
    meta = result.figure.layout.meta["gas_ratio_report_legend"]

    assert meta["schema"] == "gas-ratio-pro/report-plot-legend/v1"
    assert [entry["label"] for entry in meta["curves"]] == ["C1", "C2", "Wh"]
    assert meta["curves"][0]["description"] == "Метан"
    assert meta["fluids"][0]["label"] == "Нефть"
    assert [entry["label"] for entry in meta["markers"]] == ["Кровля", "Подошва", "Приоритет"]
    assert meta["depth_range"] == {"top": 2002.8, "base": 2016.2}


def test_pdf_and_docx_read_the_same_legend_payload() -> None:
    figure = build_professional_well_log_plot(
        _frame(),
        (_interval("gas"),),
        config=WellLogPlotConfig(track_columns=("c1", "c2")),
    ).figure

    assert pdf_legend(figure) == docx_legend(figure)
    assert pdf_legend(figure)["fluids"][0]["label"] == "Газ"


def test_print_curve_names_and_colors_are_explicit() -> None:
    figure = build_professional_well_log_plot(
        _frame(),
        (_interval(),),
        config=WellLogPlotConfig(track_columns=("c1", "c2", "wh")),
    ).figure
    visible = [trace for trace in figure.data if trace.showlegend]

    assert visible[0].name == "C1 — Метан"
    assert visible[0].line.color == "#ef4444"
    assert visible[1].name == "C2 — Этан"
    assert visible[2].name.startswith("Wh — Влажность газа")
    assert all(float(trace.line.width) >= 2.8 for trace in visible)
