from pathlib import Path

import pandas as pd

from reports.presentation_model import _track_chunks
from reports.well_log_plot import WellLogPlotConfig, build_professional_well_log_plot


ROOT = Path(__file__).resolve().parents[1]


def test_print_track_groups_are_limited_to_four_curves():
    chunks = _track_chunks(("c1", "c2", "c3", "wh", "bh", "ch", "c1_c2", "c1_c3"), 4)
    assert chunks
    assert all(len(chunk) <= 4 for chunk in chunks)


def test_print_headers_embed_min_average_and_maximum():
    frame = pd.DataFrame({
        "depth": [1000.0, 1001.0, 1002.0],
        "c1": [1.0, 2.0, 3.0],
        "wh": [10.0, 20.0, 30.0],
    })
    result = build_professional_well_log_plot(
        frame,
        config=WellLogPlotConfig(
            track_columns=("c1", "wh"),
            layout_profile="print",
            show_interval_track=True,
            auto_crop_to_active_data=False,
        ),
    )
    titles = [str(item.text or "") for item in result.figure.layout.annotations[:3]]
    assert any("min" in title and "avg" in title and "max" in title for title in titles)


def test_interactive_tablet_is_rendered_in_groups_and_selection_is_persistent():
    from app import streamlit_app as app

    groups = app._tablet_column_groups(tuple(f"curve-{index}" for index in range(17)), group_size=8)
    selections = app._normalize_plot_selections([
        {"x": 1.2, "depth": 1000.0, "figure_index": 0},
        {"x": 2.4, "depth": 1001.0, "figure_index": 1},
    ])

    assert tuple(len(group) for group in groups) == (8, 8, 1)
    assert selections[0]["depth"] == 1000.0
    assert selections[1]["figure_index"] == 1


def test_docx_does_not_repeat_unicode_symbol_legends_before_each_plot():
    source = (ROOT / "reports" / "presentation_docx.py").read_text(encoding="utf-8")
    plot_body = source.split("def _add_plot_placeholder", 1)[1].split("def render_engineering_document_docx", 1)[0]
    assert "_add_report_legend_table(doc" not in plot_body


def test_detail_statistics_are_embedded_in_plot_not_repeated_below_image():
    pdf_source = (ROOT / "reports" / "presentation_pdf.py").read_text(encoding="utf-8")
    docx_source = (ROOT / "reports" / "presentation_docx.py").read_text(encoding="utf-8")
    assert 'if str(legend.get("report_kind", "")) != "detail"' in pdf_source
    assert 'if str(legend.get("report_kind", "")) != "detail"' in docx_source
