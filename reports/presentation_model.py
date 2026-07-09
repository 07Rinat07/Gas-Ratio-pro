from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval, HydrocarbonIntervalResult
from reports.executive_summary import ExecutiveSummary
from reports.export_html import HtmlReportTable
from reports.interval_cards import IntervalReportCard
from reports.well_log_plot import WellLogPlotConfig, WellLogPlotResult, build_professional_well_log_plot


@dataclass(frozen=True)
class PresentationMetadata:
    """Stable metadata for report, UI and export renderers.

    The presentation layer must not expose low-level dataframe counters as the
    primary report content. Metadata stores neutral labels only: source, project,
    analysed interval and selected profile. Technical counters may still be
    rendered through expert appendices when explicitly requested.
    """

    source_label: str = ""
    project_label: str = ""
    depth_label: str = ""
    report_profile: str = "engineering"
    title: str = "Gas Ratio Professional Report"
    subtitle: str = "Инженерное заключение по вероятным УВ-интервалам"

    def as_report_rows(self) -> tuple[tuple[str, str], ...]:
        profile = "Инженерный" if self.report_profile == "engineering" else "Экспертный"
        rows = (
            ("Источник данных", self.source_label),
            ("Проект", self.project_label),
            ("Интервал анализа", self.depth_label),
            ("Профиль отчета", profile),
        )
        return tuple((label, value) for label, value in rows if str(value).strip())


@dataclass(frozen=True)
class PresentationModel:
    """Single presentation source for screen, reports, plots and exports.

    The model connects the already frozen Hydrocarbon Interpretation Engine with
    reporting and visualization. It intentionally contains interpreted intervals,
    executive summary, interval cards and plot data in one immutable object so
    HTML/PDF/DOCX/UI renderers do not rebuild the same engineering content with
    slightly different rules.
    """

    result: HydrocarbonIntervalResult
    executive_summary: ExecutiveSummary
    interval_cards: tuple[IntervalReportCard, ...]
    engineering_tables: tuple[HtmlReportTable, ...] = ()
    technical_tables: tuple[HtmlReportTable, ...] = ()
    well_log_plot: WellLogPlotResult | None = None
    metadata: PresentationMetadata = PresentationMetadata()
    schema: str = "gas-ratio-pro/presentation/model/v1"

    @property
    def intervals(self) -> tuple[HydrocarbonInterval, ...]:
        return self.result.intervals

    @property
    def figures(self) -> tuple[object, ...]:
        if self.well_log_plot is None:
            return ()
        return (self.well_log_plot.figure,)

    @property
    def engineer_first_tables(self) -> tuple[HtmlReportTable, ...]:
        """Tables intended for default engineering reports."""

        return self.engineering_tables

    @property
    def expert_tables(self) -> tuple[HtmlReportTable, ...]:
        """Tables intended for expert/appendix reports."""

        return self.engineering_tables + self.technical_tables


def build_presentation_model(
    *,
    result: HydrocarbonIntervalResult,
    source_df: pd.DataFrame | None = None,
    executive_summary: ExecutiveSummary,
    interval_cards: Sequence[IntervalReportCard] = (),
    engineering_tables: Sequence[HtmlReportTable | None] = (),
    technical_tables: Sequence[HtmlReportTable | None] = (),
    metadata: PresentationMetadata | None = None,
    depth_column: str = "depth",
    plot_config: WellLogPlotConfig | None = None,
    include_plot: bool = True,
) -> PresentationModel:
    """Build a presentation model from already computed interpretation sections.

    This function does not run new interpretation logic. It only composes the
    sections created from the same HIE result and optionally builds a well-log
    plot from the same dataframe and interval list.
    """

    clean_engineering_tables = tuple(table for table in engineering_tables if table is not None)
    clean_technical_tables = tuple(table for table in technical_tables if table is not None)

    plot_result: WellLogPlotResult | None = None
    if include_plot and source_df is not None and not source_df.empty:
        cfg = plot_config or WellLogPlotConfig(depth_column=depth_column)
        plot_result = build_professional_well_log_plot(source_df, result.intervals, config=cfg)

    return PresentationModel(
        result=result,
        executive_summary=executive_summary,
        interval_cards=tuple(interval_cards),
        engineering_tables=clean_engineering_tables,
        technical_tables=clean_technical_tables,
        well_log_plot=plot_result,
        metadata=metadata or PresentationMetadata(),
    )
