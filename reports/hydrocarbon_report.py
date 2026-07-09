from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from core.hydrocarbon_intervals import (
    HydrocarbonInterval,
    HydrocarbonIntervalResult,
    detect_hydrocarbon_intervals,
    hydrocarbon_interval_dataframe,
    hydrocarbon_interval_marker_dataframe,
    lithology_barrier_dataframe,
)
from reports.export_html import HtmlReportTable
from reports.executive_summary import (
    ExecutiveSummary,
    build_executive_summary,
    executive_recommendations_table,
    executive_summary_table,
    main_intervals_table,
)


@dataclass(frozen=True)
class HydrocarbonReportPayload:
    """Unified report payload for hydrocarbon interpretation exports.

    This object is intentionally presentation-neutral. HTML, future PDF/DOCX
    exporters, graph overlays and UI tables should read the same interval result
    instead of recomputing Pixler/Haworth interpretation independently.
    """

    result: HydrocarbonIntervalResult
    summary_table: HtmlReportTable | None = None
    marker_table: HtmlReportTable | None = None
    barrier_table: HtmlReportTable | None = None
    interpretation_table: HtmlReportTable | None = None
    diagnostics_table: HtmlReportTable | None = None
    executive_summary: ExecutiveSummary | None = None
    executive_summary_table: HtmlReportTable | None = None
    main_intervals_table: HtmlReportTable | None = None
    executive_recommendations_table: HtmlReportTable | None = None

    @property
    def intervals(self) -> tuple[HydrocarbonInterval, ...]:
        return self.result.intervals

    @property
    def tables(self) -> tuple[HtmlReportTable, ...]:
        """Backward-compatible technical table set used by existing exports."""

        return tuple(
            table
            for table in (
                self.summary_table,
                self.marker_table,
                self.barrier_table,
                self.interpretation_table,
                self.diagnostics_table,
            )
            if table is not None
        )

    @property
    def professional_tables(self) -> tuple[HtmlReportTable, ...]:
        """Engineer-first table sequence for Professional Reporting System."""

        return tuple(
            table
            for table in (
                self.executive_summary_table,
                self.main_intervals_table,
                self.executive_recommendations_table,
                self.summary_table,
                self.marker_table,
                self.barrier_table,
                self.interpretation_table,
                self.diagnostics_table,
            )
            if table is not None
        )

    @property
    def diagnostics(self) -> tuple[str, ...]:
        return self.result.diagnostics


def _format_cell(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def dataframe_to_html_report_table(
    title: str,
    df: pd.DataFrame,
    *,
    columns: Sequence[str] = (),
    max_rows: int | None = None,
) -> HtmlReportTable | None:
    """Convert a dataframe to the common escaped report table model."""

    if df is None or df.empty:
        return None

    table_df = df.copy()
    if columns:
        visible_columns = [column for column in columns if column in table_df.columns]
        if not visible_columns:
            return None
        table_df = table_df[visible_columns]
    if max_rows is not None and max_rows >= 0:
        table_df = table_df.head(max_rows)
    if table_df.empty:
        return None

    return HtmlReportTable(
        title=title,
        headers=tuple(str(column) for column in table_df.columns),
        rows=tuple(tuple(_format_cell(value) for value in row) for row in table_df.itertuples(index=False, name=None)),
    )


def build_hydrocarbon_interpretation_table(intervals: Sequence[HydrocarbonInterval]) -> HtmlReportTable | None:
    """Build printable engineering interpretation notes for each interval."""

    rows: list[tuple[str, str, str, str, str]] = []
    for index, interval in enumerate(intervals, start=1):
        rows.append(
            (
                f"HC-{index:03d}",
                f"{interval.top:g}-{interval.base:g}",
                interval.fluid_type,
                interval.confidence,
                interval.engineering_note,
            )
        )
    if not rows:
        return None
    return HtmlReportTable(
        title="Инженерная интерпретация УВ-интервалов",
        headers=("Маркер", "Глубина", "Тип", "Уверенность", "Интерпретация"),
        rows=tuple(rows),
    )


def build_hydrocarbon_diagnostics_table(result: HydrocarbonIntervalResult) -> HtmlReportTable | None:
    """Expose interval engine diagnostics in printable/debug reports."""

    rows = tuple((str(index), str(message)) for index, message in enumerate(result.diagnostics, start=1) if str(message).strip())
    if not rows:
        return None
    return HtmlReportTable(
        title="Диагностика движка УВ-интервалов",
        headers=("№", "Сообщение"),
        rows=rows,
    )


def build_hydrocarbon_report_payload(
    df: pd.DataFrame,
    *,
    depth_column: str = "depth",
    max_summary_rows: int | None = None,
) -> HydrocarbonReportPayload:
    """Build the single source of truth for hydrocarbon report exports.

    The payload links interval detection, printable tables, graph marker rows and
    diagnostics. This prevents Pixler, report export and chart rendering from
    producing different interval lists for the same calculated dataframe.
    """

    result = detect_hydrocarbon_intervals(df, depth_column=depth_column)
    executive_summary = build_executive_summary(result)
    interval_df = hydrocarbon_interval_dataframe(result.intervals)
    marker_df = hydrocarbon_interval_marker_dataframe(result.intervals)
    barrier_df = lithology_barrier_dataframe(result.barriers)

    summary_table = dataframe_to_html_report_table(
        "Сводка выявленных УВ-интервалов",
        interval_df,
        max_rows=max_summary_rows,
    )
    marker_table = dataframe_to_html_report_table(
        "Маркеры УВ-интервалов для графиков",
        marker_df,
        columns=(
            "marker_id",
            "top",
            "base",
            "thickness",
            "label",
            "fluid_type",
            "confidence",
            "annotation",
        ),
        max_rows=max_summary_rows,
    )
    barrier_table = dataframe_to_html_report_table(
        "Литологические перемычки между интервалами",
        barrier_df,
        columns=(
            "top",
            "base",
            "thickness",
            "lithology_label",
            "seal_quality",
            "remarks",
            "inferred",
        ),
        max_rows=max_summary_rows,
    )
    interpretation_table = build_hydrocarbon_interpretation_table(result.intervals)
    diagnostics_table = build_hydrocarbon_diagnostics_table(result)

    return HydrocarbonReportPayload(
        result=result,
        executive_summary=executive_summary,
        executive_summary_table=executive_summary_table(executive_summary),
        main_intervals_table=main_intervals_table(executive_summary),
        executive_recommendations_table=executive_recommendations_table(executive_summary),
        summary_table=summary_table,
        marker_table=marker_table,
        barrier_table=barrier_table,
        interpretation_table=interpretation_table,
        diagnostics_table=diagnostics_table,
    )
