"""Renderer-neutral readability contract for printed engineering reports.

The contract intentionally lives outside PDF/DOCX implementations.  Tests and
renderers consume the same values, so a visual rebaseline is explicit instead
of being hidden in source-text assertions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportPrintReadabilityContract:
    schema: str = "gas-ratio-pro.report-print-readability"
    version: str = "1.1"
    pdf_legend_font_pt: float = 9.5
    docx_legend_font_pt: float = 10.0
    pdf_plot_width_px: int = 2800
    pdf_plot_height_px: int = 3000
    docx_plot_width_px: int = 3200
    docx_plot_height_px: int = 2200
    legend_layout: str = "one-item-per-row"
    minimum_body_font_pt: float = 9.0
    layout_width_policy: str = "available-frame"
    plot_aspect_policy: str = "page-aware"
    landscape_minimum_frame_utilization: float = 0.90
    narrative_table_width_policy: str = "full-frame"

    @property
    def valid(self) -> bool:
        return (
            self.pdf_legend_font_pt >= 9.5
            and self.docx_legend_font_pt >= 10.0
            and self.pdf_plot_width_px >= 2400
            and self.pdf_plot_height_px >= 2000
            and self.docx_plot_width_px >= 2400
            and self.docx_plot_height_px >= 1800
            and self.legend_layout == "one-item-per-row"
            and self.minimum_body_font_pt >= 9.0
            and self.layout_width_policy == "available-frame"
            and self.plot_aspect_policy == "page-aware"
            and self.landscape_minimum_frame_utilization >= 0.90
            and self.narrative_table_width_policy == "full-frame"
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


REPORT_PRINT_READABILITY = ReportPrintReadabilityContract()


__all__ = ["REPORT_PRINT_READABILITY", "ReportPrintReadabilityContract"]
