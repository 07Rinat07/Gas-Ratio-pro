"""Renderer-neutral print layout contracts for Visualization Engine.

The print layout engine translates screen-oriented visualization geometry into
physical page geometry. It does not render SVG/PDF content and does not mutate
scene data. Concrete renderers consume the prepared page, printable-region,
scale and legend-placement contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


PAGE_SIZES_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
}
MM_TO_PT = 72.0 / 25.4


@dataclass(frozen=True, slots=True)
class PrintRect:
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True, slots=True)
class VisualizationPrintPage:
    index: int
    page_bounds: PrintRect
    printable_bounds: PrintRect
    content_bounds: PrintRect
    source_bounds: PrintRect
    content_scale: float
    legend_bounds: PrintRect | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "page_bounds": self.page_bounds.to_dict(),
            "printable_bounds": self.printable_bounds.to_dict(),
            "content_bounds": self.content_bounds.to_dict(),
            "source_bounds": self.source_bounds.to_dict(),
            "content_scale": self.content_scale,
            "legend_bounds": self.legend_bounds.to_dict() if self.legend_bounds else None,
        }


@dataclass(frozen=True, slots=True)
class VisualizationPrintLayout:
    schema: str = "visualization.print.layout"
    version: str = "1.0"
    page_size: str = "A4"
    orientation: str = "landscape"
    dpi: int = 96
    scale_mode: str = "fit_page"
    margin_mm: float = 12.0
    legend_position: str = "bottom"
    page_width_mm: float = 0.0
    page_height_mm: float = 0.0
    pages: tuple[VisualizationPrintPage, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.pages) and not any(item.startswith("print_layout_error:") for item in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "dpi": self.dpi,
            "scale_mode": self.scale_mode,
            "margin_mm": self.margin_mm,
            "legend_position": self.legend_position,
            "page_width_mm": self.page_width_mm,
            "page_height_mm": self.page_height_mm,
            "pages": [page.to_dict() for page in self.pages],
            "issues": list(self.issues),
            "metadata": dict(self.metadata),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationPrintLayoutEngine:
    """Build a deterministic single-page print placement contract."""

    DEFAULT_OPTIONS = {
        "page_size": "A4",
        "orientation": "landscape",
        "dpi": 96,
        "scale_mode": "fit_page",
        "margin_mm": 12.0,
        "legend_position": "bottom",
    }
    LEGEND_BOTTOM_PT = 46.0
    LEGEND_RIGHT_PT = 120.0

    def build(
        self,
        layout: Mapping[str, Any],
        label_legend: Mapping[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> VisualizationPrintLayout:
        cfg = dict(self.DEFAULT_OPTIONS)
        cfg.update(dict(options or {}))
        issues: list[str] = []

        page_size = str(cfg.get("page_size") or "A4").upper()
        if page_size not in PAGE_SIZES_MM:
            issues.append(f"print_layout_error:unsupported_page_size:{page_size}")
            page_size = "A4"

        orientation = str(cfg.get("orientation") or "landscape").lower()
        if orientation not in {"portrait", "landscape"}:
            issues.append(f"print_layout_error:unsupported_orientation:{orientation}")
            orientation = "landscape"

        scale_mode = str(cfg.get("scale_mode") or "fit_page").lower()
        if scale_mode not in {"fit_page", "fit_width", "actual_size"}:
            issues.append(f"print_layout_error:unsupported_scale_mode:{scale_mode}")
            scale_mode = "fit_page"

        legend_position = str(cfg.get("legend_position") or "bottom").lower()
        if legend_position not in {"bottom", "right", "none"}:
            issues.append(f"print_layout_error:unsupported_legend_position:{legend_position}")
            legend_position = "bottom"

        dpi = _positive_int(cfg.get("dpi"), 96)
        margin_mm = _non_negative_float(cfg.get("margin_mm"), 12.0)
        page_width_mm, page_height_mm = PAGE_SIZES_MM[page_size]
        if orientation == "landscape":
            page_width_mm, page_height_mm = page_height_mm, page_width_mm

        page_width_pt = page_width_mm * MM_TO_PT
        page_height_pt = page_height_mm * MM_TO_PT
        margin_pt = margin_mm * MM_TO_PT
        printable_width = page_width_pt - 2.0 * margin_pt
        printable_height = page_height_pt - 2.0 * margin_pt
        if printable_width <= 0 or printable_height <= 0:
            issues.append("print_layout_error:margins_exceed_page")
            printable_width = max(1.0, printable_width)
            printable_height = max(1.0, printable_height)

        source_width_px = _positive_float(layout.get("width"), 0.0)
        source_height_px = _positive_float(layout.get("height"), 0.0)
        if source_width_px <= 0 or source_height_px <= 0:
            issues.append("print_layout_error:invalid_source_bounds")
            source_width_px = max(1.0, source_width_px)
            source_height_px = max(1.0, source_height_px)

        legend_items = _mapping_list((label_legend or {}).get("legend_items"))
        legend_reserved = bool(legend_items) and legend_position != "none"
        content_area = PrintRect(margin_pt, margin_pt, printable_width, printable_height)
        legend_bounds: PrintRect | None = None
        if legend_reserved and legend_position == "bottom":
            reserved = min(self.LEGEND_BOTTOM_PT, max(0.0, printable_height * 0.25))
            content_area = PrintRect(margin_pt, margin_pt, printable_width, max(1.0, printable_height - reserved))
            legend_bounds = PrintRect(margin_pt, margin_pt + content_area.height, printable_width, reserved)
        elif legend_reserved and legend_position == "right":
            reserved = min(self.LEGEND_RIGHT_PT, max(0.0, printable_width * 0.30))
            content_area = PrintRect(margin_pt, margin_pt, max(1.0, printable_width - reserved), printable_height)
            legend_bounds = PrintRect(margin_pt + content_area.width, margin_pt, reserved, printable_height)

        px_to_pt = 72.0 / float(dpi)
        source_width_pt = source_width_px * px_to_pt
        source_height_pt = source_height_px * px_to_pt
        width_scale = content_area.width / source_width_pt
        height_scale = content_area.height / source_height_pt
        if scale_mode == "actual_size":
            scale = 1.0
        elif scale_mode == "fit_width":
            scale = width_scale
        else:
            scale = min(width_scale, height_scale)
        scale = max(0.01, min(scale, 1.0))

        scaled_width = source_width_pt * scale
        scaled_height = source_height_pt * scale
        origin_x = content_area.x + max(0.0, (content_area.width - scaled_width) / 2.0)
        origin_y = content_area.y + max(0.0, (content_area.height - scaled_height) / 2.0)
        page = VisualizationPrintPage(
            index=1,
            page_bounds=PrintRect(0.0, 0.0, page_width_pt, page_height_pt),
            printable_bounds=PrintRect(margin_pt, margin_pt, printable_width, printable_height),
            content_bounds=PrintRect(origin_x, origin_y, scaled_width, scaled_height),
            source_bounds=PrintRect(0.0, 0.0, source_width_px, source_height_px),
            content_scale=scale,
            legend_bounds=legend_bounds,
        )
        return VisualizationPrintLayout(
            page_size=page_size,
            orientation=orientation,
            dpi=dpi,
            scale_mode=scale_mode,
            margin_mm=margin_mm,
            legend_position=legend_position,
            page_width_mm=page_width_mm,
            page_height_mm=page_height_mm,
            pages=(page,),
            issues=tuple(issues),
            metadata={
                "page_count": 1,
                "legend_item_count": len(legend_items),
                "legend_reserved": legend_reserved,
                "source_width_px": source_width_px,
                "source_height_px": source_height_px,
                "source_width_pt": source_width_pt,
                "source_height_pt": source_height_pt,
                "printable_width_pt": printable_width,
                "printable_height_pt": printable_height,
                "content_scale": scale,
                "multi_page_supported": False,
                "raw_dataframe_included": False,
                "ui_objects_included": False,
            },
        )


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in value] if isinstance(value, (list, tuple)) else []


def _positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _non_negative_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
