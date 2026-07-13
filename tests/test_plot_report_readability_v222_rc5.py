from __future__ import annotations

import plotly.graph_objects as go

from palettes.plot_engine import ENGINEERING_COLORS, THEME, normalize_trace_style
from reports.presentation_docx import _adaptive_docx_column_widths
from reports.presentation_pdf import _adaptive_pdf_column_widths


def test_plot_theme_enforces_readable_lines_and_markers() -> None:
    figure = go.Figure(go.Scatter(x=[1, 2], y=[2, 3], mode="lines+markers", line={"width": 0.8}, marker={"size": 4}))
    normalize_trace_style(figure)
    assert figure.data[0].line.width >= 2.0
    assert figure.data[0].marker.size >= 9
    assert THEME.grid_color.endswith("0.34)")


def test_engineering_palette_is_high_contrast() -> None:
    assert ENGINEERING_COLORS["oil"] == "#22d3ee"
    assert ENGINEERING_COLORS["gas"] == "#fbbf24"
    assert ENGINEERING_COLORS["condensate"] == "#fb7185"


def test_pdf_column_widths_fill_printable_area() -> None:
    widths = _adaptive_pdf_column_widths(
        ("ID", "Интервал", "Инженерный вывод"),
        (("HC-001", "2000–2010", "Длинное инженерное заключение для проверки ширины"),),
    )
    assert len(widths) == 3
    assert widths[2] > widths[0]
    assert all(width > 0 for width in widths)


def test_docx_column_widths_favour_narrative_columns() -> None:
    widths = _adaptive_docx_column_widths(
        ("ID", "Флюид", "Рекомендация"),
        (("HC-001", "Нефть", "Сопоставить с ГИС, керном и результатами испытаний"),),
    )
    assert len(widths) == 3
    assert widths[2] > widths[0]
    assert abs(sum(widths) - 6.6) < 0.01
