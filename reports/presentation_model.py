from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence, Any

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval, HydrocarbonIntervalResult
from reports.executive_summary import ExecutiveSummary
from reports.export_html import HtmlReportTable
from reports.interval_cards import IntervalReportCard
from app.visualization_v3.composite_v4 import build_composite_log_v4
from app.visualization_v3.composite_engine import CompositeLogResult
from reports.well_log_plot import (
    WellLogPlotConfig, WellLogPlotResult, build_professional_well_log_plot,
    group_intervals_for_report, adaptive_detail_padding, FLUID_PLOT_LABELS,
)


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
        profile_map = {"client": "Для заказчика", "engineering": "Инженерный", "expert": "Экспертный"}
        profile = profile_map.get(str(self.report_profile).strip().lower(), "Инженерный")
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
    well_log_plot: object | None = None
    detail_well_log_plots: tuple[object, ...] = ()
    visualization_payloads: tuple[Mapping[str, Any], ...] = ()
    metadata: PresentationMetadata = PresentationMetadata()
    schema: str = "gas-ratio-pro/presentation/model/v1"

    @property
    def intervals(self) -> tuple[HydrocarbonInterval, ...]:
        return self.result.intervals

    @property
    def figures(self) -> tuple[object, ...]:
        figures: list[object] = []
        if self.well_log_plot is not None:
            figures.append(getattr(self.well_log_plot, "figure", self.well_log_plot))
        figures.extend(getattr(item, "figure", item) for item in self.detail_well_log_plots)
        return tuple(figures)

    @property
    def visualization_previews(self) -> tuple[Mapping[str, Any], ...]:
        """Renderer-neutral visualization preview payloads attached to reports.

        The presentation model stores already prepared Visualization Engine
        payloads. Exporters may embed their lightweight previews, but must not
        rebuild LAS tracks, recalculate intervals or inspect raw dataframes.
        """

        previews: list[Mapping[str, Any]] = []
        for payload in self.visualization_payloads:
            preview = dict(payload.get("preview", {}) or {})
            if preview.get("kind") and preview.get("export_ready"):
                previews.append(preview)
        return tuple(previews)

    @property
    def engineer_first_tables(self) -> tuple[HtmlReportTable, ...]:
        """Tables intended for default engineering reports."""

        return self.engineering_tables

    @property
    def expert_tables(self) -> tuple[HtmlReportTable, ...]:
        """Tables intended for expert/appendix reports."""

        return self.engineering_tables + self.technical_tables


def _track_chunks(columns: Sequence[str], size: int = 5) -> tuple[tuple[str, ...], ...]:
    clean = tuple(str(c) for c in columns if str(c))
    return tuple(clean[i:i + max(1, size)] for i in range(0, len(clean), max(1, size))) or ((),)


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
    visualization_payloads: Sequence[Mapping[str, Any]] = (),
) -> PresentationModel:
    """Build a presentation model from already computed interpretation sections.

    This function does not run new interpretation logic. It only composes the
    sections created from the same HIE result and optionally builds a well-log
    plot from the same dataframe and interval list.
    """

    clean_engineering_tables = tuple(table for table in engineering_tables if table is not None)
    clean_technical_tables = tuple(table for table in technical_tables if table is not None)

    plot_result: object | None = None
    detail_results: list[object] = []
    if include_plot and source_df is not None and not source_df.empty:
        cfg = plot_config or WellLogPlotConfig(depth_column=depth_column)
        report_tracks = ("tgas", "c1", "c2", "c3", "wh", "bh", "ch", "inverse_oil_indicator")
        plot_result = build_composite_log_v4(
            source_df, intervals=result.intervals,
            title="Обзорный инженерный планшет",
            report_title="Обзорный планшет скважины", report_kind="overview",
            height=max(4200, cfg.height), target_width=6200, include_keys=report_tracks,
        )

        profile = str((metadata or PresentationMetadata()).report_profile or "engineering").lower()
        max_groups = 5 if profile in {"client", "customer"} else (30 if profile == "expert" else 15)
        groups = group_intervals_for_report(result.intervals, max_groups=max_groups) if len(result.intervals) > 1 else ()
        depth_name = next((str(c) for c in source_df.columns if str(c).strip().lower() in {str(cfg.depth_column).lower(), "depth", "dept", "md"}), None)
        numeric_depth = pd.to_numeric(source_df[depth_name], errors="coerce") if depth_name else None
        for group in groups:
            fluids = ", ".join(dict.fromkeys(FLUID_PLOT_LABELS.get(str(i.fluid_type), str(i.fluid_type)) for i in group.intervals))
            padding = adaptive_detail_padding(group.top, group.base)
            detail_df = source_df
            if numeric_depth is not None:
                detail_df = source_df.loc[numeric_depth.between(group.top-padding, group.base+padding)].copy()
            detail_results.append(build_composite_log_v4(
                detail_df, intervals=group.intervals,
                title=f"Инженерный планшет · {group.top:g}–{group.base:g} м",
                report_title=f"Интервал {group.index}: {group.top:g}–{group.base:g} м · {fluids}",
                report_kind="detail", height=max(4200, cfg.height), target_width=6200,
                include_keys=report_tracks,
            ))

    return PresentationModel(
        result=result,
        executive_summary=executive_summary,
        interval_cards=tuple(interval_cards),
        engineering_tables=clean_engineering_tables,
        technical_tables=clean_technical_tables,
        well_log_plot=plot_result,
        detail_well_log_plots=tuple(detail_results),
        visualization_payloads=tuple(dict(payload) for payload in visualization_payloads),
        metadata=metadata or PresentationMetadata(),
    )
