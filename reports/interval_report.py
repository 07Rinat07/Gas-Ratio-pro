from __future__ import annotations

from typing import Sequence

import pandas as pd

from reports.export_html import HtmlReportMetadata, HtmlReportTable, build_plotly_html_report
from core.hydrocarbon_intervals import (
    detect_hydrocarbon_intervals,
    hydrocarbon_interval_dataframe,
    hydrocarbon_interval_marker_dataframe,
)


def _format_cell(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def dataframe_to_report_table(title: str, df: pd.DataFrame, *, max_rows: int | None = None) -> HtmlReportTable | None:
    """Convert a dataframe into a small escaped HTML report table model.

    The helper intentionally performs only display formatting. It does not mutate
    engineering data, and it keeps the original column order so the printed
    interval table matches the table shown in the Streamlit workflow.
    """

    if df is None or df.empty:
        return None

    table_df = df.copy()
    if max_rows is not None and max_rows >= 0:
        table_df = table_df.head(max_rows)
    if table_df.empty:
        return None

    return HtmlReportTable(
        title=title,
        headers=tuple(str(column) for column in table_df.columns),
        rows=tuple(tuple(_format_cell(value) for value in row) for row in table_df.itertuples(index=False, name=None)),
    )


def build_numeric_statistics_table(
    df: pd.DataFrame,
    *,
    columns: Sequence[str] = (),
    title: str = "Статистика выбранного интервала",
) -> HtmlReportTable | None:
    """Build min/max/mean/count table for selected numeric interval curves."""

    if df is None or df.empty:
        return None

    selected_columns = tuple(str(column) for column in columns if str(column) in df.columns)
    if not selected_columns:
        selected_columns = tuple(str(column) for column in df.columns)

    rows: list[tuple[str, str, str, str, str]] = []
    for column in selected_columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            (
                column,
                f"{float(values.min()):g}",
                f"{float(values.max()):g}",
                f"{float(values.mean()):g}",
                str(int(values.count())),
            )
        )

    if not rows:
        return None
    return HtmlReportTable(
        title=title,
        headers=("Параметр", "Min", "Max", "Mean", "N"),
        rows=tuple(rows),
    )


def build_interpretation_counts_table(df: pd.DataFrame, *, column: str = "interpretation") -> HtmlReportTable | None:
    """Build count table for preliminary interpretation classes."""

    if df is None or df.empty or column not in df.columns:
        return None

    values = df[column].fillna("not classified").astype(str).str.strip().replace("", "not classified")
    counts = values.value_counts(dropna=False)
    if counts.empty:
        return None
    return HtmlReportTable(
        title="Сводка предварительной интерпретации",
        headers=("Класс", "Строк"),
        rows=tuple((str(label), str(int(count))) for label, count in counts.items()),
    )


def build_hydrocarbon_interval_summary_table(df: pd.DataFrame) -> HtmlReportTable | None:
    """Build report-ready summary of all detected hydrocarbon intervals.

    This table is intentionally separated from the raw selected interval table:
    it represents interpreted oil/gas/condensate candidates and is the future
    input model for marked graphs and PDF export.
    """

    result = detect_hydrocarbon_intervals(df)
    interval_df = hydrocarbon_interval_dataframe(result.intervals)
    if interval_df.empty:
        return None
    return dataframe_to_report_table("Сводка выявленных УВ-интервалов", interval_df)


def build_hydrocarbon_marker_table(df: pd.DataFrame) -> HtmlReportTable | None:
    """Build printable marker table for graph overlays and report annotations."""

    result = detect_hydrocarbon_intervals(df)
    marker_df = hydrocarbon_interval_marker_dataframe(result.intervals)
    if marker_df.empty:
        return None
    visible_columns = [
        "marker_id",
        "top",
        "base",
        "thickness",
        "label",
        "fluid_type",
        "confidence",
        "annotation",
    ]
    return dataframe_to_report_table("Маркеры УВ-интервалов для графиков", marker_df[visible_columns])


def build_interval_print_report(
    figures,
    *,
    title: str,
    source_label: str,
    project_label: str,
    depth_label: str,
    interval_df: pd.DataFrame,
    tablet_columns: Sequence[str] = (),
    extra_tables: Sequence[HtmlReportTable] = (),
    notes: Sequence[str] = (),
    max_interval_rows: int = 120,
) -> bytes:
    """Create a complete printable HTML report for the selected depth interval.

    The report combines charts, interpretation counts, numeric statistics,
    marker/zone tables and a bounded interval table. A bounded raw table keeps
    browser printing stable while CSV/XLSX exports remain the source for full
    machine-readable data.
    """

    rows_count = 0 if interval_df is None else len(interval_df)
    selected_tablet_columns = tuple(str(column) for column in tablet_columns if str(column).strip())
    tables: list[HtmlReportTable] = []

    hydrocarbon_summary_table = build_hydrocarbon_interval_summary_table(interval_df)
    if hydrocarbon_summary_table is not None:
        tables.append(hydrocarbon_summary_table)

    marker_table = build_hydrocarbon_marker_table(interval_df)
    if marker_table is not None:
        tables.append(marker_table)

    interpretation_table = build_interpretation_counts_table(interval_df)
    if interpretation_table is not None:
        tables.append(interpretation_table)

    stats_table = build_numeric_statistics_table(interval_df, columns=selected_tablet_columns)
    if stats_table is not None:
        tables.append(stats_table)

    tables.extend(table for table in extra_tables if table is not None)

    interval_table = dataframe_to_report_table(
        f"Таблица выбранного интервала (первые {min(rows_count, max_interval_rows)} из {rows_count} строк)",
        interval_df,
        max_rows=max_interval_rows,
    )
    if interval_table is not None:
        tables.append(interval_table)

    report_notes = tuple(str(note) for note in notes if str(note).strip()) + (
        "Интерпретация является предварительной инженерной подсказкой и требует проверки по ГИС, литологии, буровому контексту и качеству данных.",
    )

    return build_plotly_html_report(
        figures,
        HtmlReportMetadata(
            title=title,
            subtitle="Печатный отчет по выбранному интервалу",
            rows=(
                ("Источник данных", str(source_label)),
                ("Проект", str(project_label)),
                ("Диапазон глубины", str(depth_label)),
                ("Строк в интервале", str(rows_count)),
                ("Планшетные параметры", ", ".join(selected_tablet_columns) if selected_tablet_columns else "не выбраны"),
            ),
            notes=report_notes,
            tables=tuple(tables),
        ),
    )
