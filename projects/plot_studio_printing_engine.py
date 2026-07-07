from __future__ import annotations

"""Renderer-independent Plot Studio printing engine.

The printing layer converts a Plot Studio workspace and tablet layout into a
print-ready manifest: page format, orientation, margins, printable area,
track-to-page scaling, page count and print/export hints.  It does not render
figures and does not modify LAS/project source data.
"""

from dataclasses import dataclass
from typing import Any, Literal

from projects.plot_studio_core import PlotWorkspace
from projects.plot_studio_track_layout import (
    PlotTrackLayoutConfig,
    PlotTrackLayoutResult,
    build_plot_track_layout,
    build_plot_track_layout_manifest,
)

PlotPrintPageSize = Literal["a4", "a3", "a2", "a1", "a0", "letter"]
PlotPrintOrientation = Literal["portrait", "landscape"]
PlotPrintScaleMode = Literal["fit_width", "fit_page", "fixed_scale"]

PLOT_PRINT_PAGE_SIZES_MM: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "a3": (297.0, 420.0),
    "a2": (420.0, 594.0),
    "a1": (594.0, 841.0),
    "a0": (841.0, 1189.0),
    "letter": (215.9, 279.4),
}


@dataclass(frozen=True)
class PlotPrintConfig:
    """Page and scale settings for professional tablet printing."""

    page_size: PlotPrintPageSize = "a3"
    orientation: PlotPrintOrientation = "portrait"
    dpi: int = 300
    margin_top_mm: float = 12.0
    margin_right_mm: float = 10.0
    margin_bottom_mm: float = 12.0
    margin_left_mm: float = 10.0
    scale_mode: PlotPrintScaleMode = "fit_width"
    fixed_scale: float = 1.0
    include_header: bool = True
    include_footer: bool = True
    include_legend: bool = True
    include_page_numbers: bool = True
    repeat_depth_track: bool = True


@dataclass(frozen=True)
class PlotPrintPage:
    """One logical print page prepared for renderer/print UI."""

    page_number: int
    depth_from: float
    depth_to: float
    width_px: int
    height_px: int
    printable_width_px: int
    printable_height_px: int
    scale: float


@dataclass(frozen=True)
class PlotPrintManifest:
    """Complete print manifest for UI, export engine and operation journal."""

    workspace_id: str
    workspace_name: str
    well_id: str
    page_size: PlotPrintPageSize
    orientation: PlotPrintOrientation
    dpi: int
    page_width_mm: float
    page_height_mm: float
    printable_width_mm: float
    printable_height_mm: float
    page_width_px: int
    page_height_px: int
    printable_width_px: int
    printable_height_px: int
    scale_mode: PlotPrintScaleMode
    scale: float
    page_count: int
    layout: dict[str, Any]
    pages: tuple[PlotPrintPage, ...]
    options: dict[str, bool]
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlotPrintJob:
    """Validated print job descriptor."""

    manifest: PlotPrintManifest
    ready: bool
    messages: tuple[str, ...] = ()


def _finite_float(value: Any, field_label: str) -> float:
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{field_label}: значение должно быть конечным числом.")
    return number


def _positive_int(value: Any, field_label: str) -> int:
    number = _finite_float(value, field_label)
    if number <= 0:
        raise ValueError(f"{field_label}: значение должно быть больше нуля.")
    return int(round(number))


def _non_negative_float(value: Any, field_label: str) -> float:
    number = _finite_float(value, field_label)
    if number < 0:
        raise ValueError(f"{field_label}: значение не может быть отрицательным.")
    return number


def _positive_float(value: Any, field_label: str) -> float:
    number = _finite_float(value, field_label)
    if number <= 0:
        raise ValueError(f"{field_label}: значение должно быть больше нуля.")
    return number


def validate_plot_print_config(config: PlotPrintConfig | None = None) -> PlotPrintConfig:
    """Validate and normalize print configuration."""

    cfg = config or PlotPrintConfig()
    page_size = str(cfg.page_size or "a3").strip().lower()
    if page_size not in PLOT_PRINT_PAGE_SIZES_MM:
        raise ValueError("Print page size: поддерживаются A4, A3, A2, A1, A0 и Letter.")
    orientation = str(cfg.orientation or "portrait").strip().lower()
    if orientation not in {"portrait", "landscape"}:
        raise ValueError("Print orientation: поддерживаются portrait и landscape.")
    scale_mode = str(cfg.scale_mode or "fit_width").strip().lower()
    if scale_mode not in {"fit_width", "fit_page", "fixed_scale"}:
        raise ValueError("Print scale mode: поддерживаются fit_width, fit_page и fixed_scale.")
    dpi = _positive_int(cfg.dpi, "Print DPI")
    if dpi < 72 or dpi > 1200:
        raise ValueError("Print DPI: допустимый диапазон 72..1200.")
    fixed_scale = _positive_float(cfg.fixed_scale, "Print fixed scale")
    if fixed_scale < 0.1 or fixed_scale > 8.0:
        raise ValueError("Print fixed scale: допустимый диапазон 0.1..8.0.")

    margins = (
        _non_negative_float(cfg.margin_top_mm, "Print top margin"),
        _non_negative_float(cfg.margin_right_mm, "Print right margin"),
        _non_negative_float(cfg.margin_bottom_mm, "Print bottom margin"),
        _non_negative_float(cfg.margin_left_mm, "Print left margin"),
    )
    page_width, page_height = _oriented_page_size_mm(page_size, orientation)  # type: ignore[arg-type]
    if margins[1] + margins[3] >= page_width:
        raise ValueError("Print margins: левое и правое поля превышают ширину страницы.")
    if margins[0] + margins[2] >= page_height:
        raise ValueError("Print margins: верхнее и нижнее поля превышают высоту страницы.")

    return PlotPrintConfig(
        page_size=page_size,  # type: ignore[arg-type]
        orientation=orientation,  # type: ignore[arg-type]
        dpi=dpi,
        margin_top_mm=margins[0],
        margin_right_mm=margins[1],
        margin_bottom_mm=margins[2],
        margin_left_mm=margins[3],
        scale_mode=scale_mode,  # type: ignore[arg-type]
        fixed_scale=fixed_scale,
        include_header=bool(cfg.include_header),
        include_footer=bool(cfg.include_footer),
        include_legend=bool(cfg.include_legend),
        include_page_numbers=bool(cfg.include_page_numbers),
        repeat_depth_track=bool(cfg.repeat_depth_track),
    )


def _oriented_page_size_mm(page_size: PlotPrintPageSize, orientation: PlotPrintOrientation) -> tuple[float, float]:
    width, height = PLOT_PRINT_PAGE_SIZES_MM[page_size]
    if orientation == "landscape":
        return max(width, height), min(width, height)
    return min(width, height), max(width, height)


def _mm_to_px(mm: float, dpi: int) -> int:
    return max(1, int(round(mm / 25.4 * dpi)))


def _depth_pages(workspace: PlotWorkspace, page_count: int, page_width_px: int, page_height_px: int, printable_width_px: int, printable_height_px: int, scale: float) -> tuple[PlotPrintPage, ...]:
    depth = workspace.viewport.depth_range
    height = depth.height_m
    if page_count <= 1:
        return (
            PlotPrintPage(
                page_number=1,
                depth_from=depth.from_md,
                depth_to=depth.to_md,
                width_px=page_width_px,
                height_px=page_height_px,
                printable_width_px=printable_width_px,
                printable_height_px=printable_height_px,
                scale=scale,
            ),
        )
    step = height / page_count
    pages: list[PlotPrintPage] = []
    for index in range(page_count):
        depth_from = depth.from_md + step * index
        depth_to = depth.to_md if index == page_count - 1 else depth.from_md + step * (index + 1)
        pages.append(
            PlotPrintPage(
                page_number=index + 1,
                depth_from=round(depth_from, 6),
                depth_to=round(depth_to, 6),
                width_px=page_width_px,
                height_px=page_height_px,
                printable_width_px=printable_width_px,
                printable_height_px=printable_height_px,
                scale=scale,
            )
        )
    return tuple(pages)


def build_plot_print_manifest(
    workspace: PlotWorkspace,
    *,
    layout: PlotTrackLayoutResult | None = None,
    layout_config: PlotTrackLayoutConfig | None = None,
    print_config: PlotPrintConfig | None = None,
) -> PlotPrintManifest:
    """Build a print-ready manifest without writing files."""

    cfg = validate_plot_print_config(print_config)
    actual_layout = layout or build_plot_track_layout(workspace, config=layout_config)
    page_width_mm, page_height_mm = _oriented_page_size_mm(cfg.page_size, cfg.orientation)
    printable_width_mm = page_width_mm - cfg.margin_left_mm - cfg.margin_right_mm
    printable_height_mm = page_height_mm - cfg.margin_top_mm - cfg.margin_bottom_mm
    page_width_px = _mm_to_px(page_width_mm, cfg.dpi)
    page_height_px = _mm_to_px(page_height_mm, cfg.dpi)
    printable_width_px = _mm_to_px(printable_width_mm, cfg.dpi)
    printable_height_px = _mm_to_px(printable_height_mm, cfg.dpi)

    layout_width = max(actual_layout.total_width_px, actual_layout.canvas_width_px, 1)
    layout_height = max(int(round(workspace.viewport.depth_range.height_m)), 1)
    fit_width_scale = printable_width_px / layout_width
    fit_height_scale = printable_height_px / layout_height
    if cfg.scale_mode == "fit_page":
        scale = min(fit_width_scale, fit_height_scale)
    elif cfg.scale_mode == "fixed_scale":
        scale = cfg.fixed_scale
    else:
        scale = fit_width_scale
    scale = round(max(scale, 0.01), 6)

    scaled_height_px = max(1, int(round(layout_height * scale)))
    page_count = max(1, (scaled_height_px + printable_height_px - 1) // printable_height_px)
    messages = list(actual_layout.messages)
    if workspace.issues:
        messages.extend(workspace.issues)
    if page_count > 1:
        messages.append(f"Планшет будет разбит на {page_count} страниц по глубине.")

    pages = _depth_pages(workspace, page_count, page_width_px, page_height_px, printable_width_px, printable_height_px, scale)
    return PlotPrintManifest(
        workspace_id=workspace.template_id,
        workspace_name=workspace.name,
        well_id=workspace.well_id,
        page_size=cfg.page_size,
        orientation=cfg.orientation,
        dpi=cfg.dpi,
        page_width_mm=page_width_mm,
        page_height_mm=page_height_mm,
        printable_width_mm=round(printable_width_mm, 3),
        printable_height_mm=round(printable_height_mm, 3),
        page_width_px=page_width_px,
        page_height_px=page_height_px,
        printable_width_px=printable_width_px,
        printable_height_px=printable_height_px,
        scale_mode=cfg.scale_mode,
        scale=scale,
        page_count=page_count,
        layout=build_plot_track_layout_manifest(actual_layout),
        pages=pages,
        options={
            "include_header": cfg.include_header,
            "include_footer": cfg.include_footer,
            "include_legend": cfg.include_legend,
            "include_page_numbers": cfg.include_page_numbers,
            "repeat_depth_track": cfg.repeat_depth_track,
        },
        messages=tuple(messages),
    )


def create_plot_print_job(
    workspace: PlotWorkspace,
    *,
    layout: PlotTrackLayoutResult | None = None,
    layout_config: PlotTrackLayoutConfig | None = None,
    print_config: PlotPrintConfig | None = None,
) -> PlotPrintJob:
    """Create a validated print job descriptor for UI and export layers."""

    manifest = build_plot_print_manifest(workspace, layout=layout, layout_config=layout_config, print_config=print_config)
    messages = list(manifest.messages)
    ready = bool(workspace.tracks) and manifest.printable_width_px > 0 and manifest.printable_height_px > 0
    if not workspace.tracks:
        messages.append("Печать невозможна: нет видимых треков Plot Studio.")
        ready = False
    return PlotPrintJob(manifest=manifest, ready=ready, messages=tuple(messages))


def build_plot_print_manifest_dict(manifest: PlotPrintManifest) -> dict[str, Any]:
    """Return JSON-serializable print manifest."""

    return {
        "workspace_id": manifest.workspace_id,
        "workspace_name": manifest.workspace_name,
        "well_id": manifest.well_id,
        "page_size": manifest.page_size,
        "orientation": manifest.orientation,
        "dpi": manifest.dpi,
        "page_width_mm": manifest.page_width_mm,
        "page_height_mm": manifest.page_height_mm,
        "printable_width_mm": manifest.printable_width_mm,
        "printable_height_mm": manifest.printable_height_mm,
        "page_width_px": manifest.page_width_px,
        "page_height_px": manifest.page_height_px,
        "printable_width_px": manifest.printable_width_px,
        "printable_height_px": manifest.printable_height_px,
        "scale_mode": manifest.scale_mode,
        "scale": manifest.scale,
        "page_count": manifest.page_count,
        "layout": manifest.layout,
        "pages": [page.__dict__ for page in manifest.pages],
        "options": manifest.options,
        "messages": list(manifest.messages),
    }


def build_plot_print_page_table(manifest: PlotPrintManifest) -> tuple[dict[str, Any], ...]:
    """Build compact page table for Streamlit preview."""

    return tuple(
        {
            "Страница": page.page_number,
            "Depth From": page.depth_from,
            "Depth To": page.depth_to,
            "Ширина печати, px": page.printable_width_px,
            "Высота печати, px": page.printable_height_px,
            "Масштаб": page.scale,
        }
        for page in manifest.pages
    )
