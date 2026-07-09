from __future__ import annotations

from typing import Literal, Sequence

import pandas as pd

from reports.export_html import HtmlReportMetadata, HtmlReportTable, build_plotly_html_report
from reports.hydrocarbon_report import build_hydrocarbon_report_payload


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
    """Build report-ready summary through the unified hydrocarbon payload."""

    return build_hydrocarbon_report_payload(df).summary_table


def build_hydrocarbon_marker_table(df: pd.DataFrame) -> HtmlReportTable | None:
    """Build printable marker table through the unified hydrocarbon payload."""

    return build_hydrocarbon_report_payload(df).marker_table


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
    report_profile: Literal["engineering", "expert"] = "engineering",
) -> bytes:
    """Create a complete printable HTML report for the selected depth interval.

    The default ``engineering`` profile is intentionally engineer-first: it
    starts with conclusions, intervals, recommendations and limitations, and it
    does not print raw dataframe row counts, min/max tables or full technical
    dumps. Those details remain available through the ``expert`` profile and
    machine-readable CSV/XLSX exports. This keeps the printed report focused on
    what a practicing geologist or mud-logging engineer needs first: where the
    probable accumulations are and why the interpretation was made.
    """

    profile = str(report_profile or "engineering").strip().lower()
    if profile not in {"engineering", "expert"}:
        profile = "engineering"

    rows_count = 0 if interval_df is None else len(interval_df)
    selected_tablet_columns = tuple(str(column) for column in tablet_columns if str(column).strip())
    tables: list[HtmlReportTable] = []

    hydrocarbon_payload = build_hydrocarbon_report_payload(
        interval_df,
        source_label=str(source_label),
        project_label=str(project_label),
        depth_label=str(depth_label),
        report_profile=profile,
    )
    if hydrocarbon_payload.presentation_model is not None:
        if profile == "expert":
            tables.extend(hydrocarbon_payload.presentation_model.expert_tables)
        else:
            tables.extend(hydrocarbon_payload.presentation_model.engineer_first_tables)
    else:
        tables.extend(hydrocarbon_payload.professional_tables)

    if profile == "expert":
        interpretation_table = build_interpretation_counts_table(interval_df)
        if interpretation_table is not None:
            tables.append(interpretation_table)

        stats_table = build_numeric_statistics_table(interval_df, columns=selected_tablet_columns)
        if stats_table is not None:
            tables.append(stats_table)

    tables.extend(table for table in extra_tables if table is not None)

    if profile == "expert":
        interval_table = dataframe_to_report_table(
            f"Техническая таблица данных (первые {min(rows_count, max_interval_rows)} из {rows_count} строк)",
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
            subtitle="Печатный отчет по выбранному интервалу · Инженерное заключение по вероятным УВ-интервалам",
            rows=(
                ("Источник данных", str(source_label)),
                ("Проект", str(project_label)),
                ("Интервал анализа", str(depth_label)),
                ("Профиль отчета", "Инженерный" if profile == "engineering" else "Экспертный"),
            ),
            notes=report_notes,
            tables=tuple(tables),
        ),
    )
