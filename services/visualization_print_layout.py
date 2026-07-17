"""Renderer-neutral physical page layout for Visualization Engine exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.physical_print_profiles import PAGE_SIZES_MM, resolve_physical_print_profile


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
    track_ids: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "page_bounds": self.page_bounds.to_dict(),
            "printable_bounds": self.printable_bounds.to_dict(),
            "content_bounds": self.content_bounds.to_dict(),
            "source_bounds": self.source_bounds.to_dict(),
            "content_scale": self.content_scale,
            "legend_bounds": self.legend_bounds.to_dict() if self.legend_bounds else None,
            "track_ids": list(self.track_ids),
        }


@dataclass(frozen=True, slots=True)
class VisualizationPrintLayout:
    schema: str = "visualization.print.layout"
    version: str = "2.0"
    profile_id: str = "a4_landscape"
    page_size: str = "A4"
    orientation: str = "landscape"
    dpi: int = 96
    scale_mode: str = "fit_page"
    margin_mm: float = 12.0
    legend_position: str = "bottom"
    page_width_mm: float = 0.0
    page_height_mm: float = 0.0
    minimum_font_pt: float = 7.5
    minimum_line_width_pt: float = 0.5
    minimum_track_width_mm: float = 28.0
    max_tracks_per_page: int = 6
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
            "profile_id": self.profile_id,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "dpi": self.dpi,
            "scale_mode": self.scale_mode,
            "margin_mm": self.margin_mm,
            "legend_position": self.legend_position,
            "page_width_mm": self.page_width_mm,
            "page_height_mm": self.page_height_mm,
            "minimum_font_pt": self.minimum_font_pt,
            "minimum_line_width_pt": self.minimum_line_width_pt,
            "minimum_track_width_mm": self.minimum_track_width_mm,
            "max_tracks_per_page": self.max_tracks_per_page,
            "pages": [page.to_dict() for page in self.pages],
            "issues": list(self.issues),
            "metadata": dict(self.metadata),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationPrintLayoutEngine:
    """Build deterministic pages without shrinking wide track sets below profile floors."""

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

        requested_profile_id = str(cfg.get("profile_id") or "").strip().lower()
        try:
            profile = resolve_physical_print_profile(page_size, orientation, requested_profile_id or None)
        except KeyError:
            issues.append(f"print_layout_error:unsupported_profile:{requested_profile_id}")
            profile = resolve_physical_print_profile(page_size, orientation)
        if requested_profile_id:
            page_size = profile.page_size
            orientation = profile.orientation

        dpi = _positive_int(cfg.get("dpi"), profile.dpi)
        margin_mm = _non_negative_float(cfg.get("margin_mm"), profile.margin_mm)
        minimum_font_pt = max(profile.minimum_font_pt, _positive_float(cfg.get("minimum_font_pt"), profile.minimum_font_pt))
        minimum_line_width_pt = max(
            profile.minimum_line_width_pt,
            _positive_float(cfg.get("minimum_line_width_pt"), profile.minimum_line_width_pt),
        )
        minimum_track_width_mm = max(
            profile.minimum_track_width_mm,
            _positive_float(cfg.get("minimum_track_width_mm"), profile.minimum_track_width_mm),
        )
        requested_max_tracks = _positive_int(cfg.get("max_tracks_per_page"), profile.max_tracks_per_page)
        max_tracks_per_page = min(profile.max_tracks_per_page, requested_max_tracks)

        page_width_mm, page_height_mm = profile.page_width_mm, profile.page_height_mm
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
        tracks = _print_tracks(layout)
        track_groups = self._paginate_tracks(
            tracks,
            source_height_px=source_height_px,
            content_area=content_area,
            px_to_pt=px_to_pt,
            scale_mode=scale_mode,
            minimum_track_width_mm=minimum_track_width_mm,
            max_tracks_per_page=max_tracks_per_page,
        )
        if not track_groups:
            track_groups = [([], PrintRect(0.0, 0.0, source_width_px, source_height_px))]

        pages: list[VisualizationPrintPage] = []
        for page_index, (group, source_bounds) in enumerate(track_groups, start=1):
            scale = _content_scale(
                source_bounds.width * px_to_pt,
                source_bounds.height * px_to_pt,
                content_area,
                scale_mode,
            )
            scaled_width = source_bounds.width * px_to_pt * scale
            scaled_height = source_bounds.height * px_to_pt * scale
            origin_x = content_area.x + max(0.0, (content_area.width - scaled_width) / 2.0)
            origin_y = content_area.y + max(0.0, (content_area.height - scaled_height) / 2.0)
            track_ids = tuple(str(item.get("id") or "") for item in group if str(item.get("id") or ""))
            pages.append(
                VisualizationPrintPage(
                    index=page_index,
                    page_bounds=PrintRect(0.0, 0.0, page_width_pt, page_height_pt),
                    printable_bounds=PrintRect(margin_pt, margin_pt, printable_width, printable_height),
                    content_bounds=PrintRect(origin_x, origin_y, scaled_width, scaled_height),
                    source_bounds=source_bounds,
                    content_scale=scale,
                    legend_bounds=legend_bounds,
                    track_ids=track_ids,
                )
            )

        source_width_pt = source_width_px * px_to_pt
        source_height_pt = source_height_px * px_to_pt
        return VisualizationPrintLayout(
            profile_id=profile.id,
            page_size=page_size,
            orientation=orientation,
            dpi=dpi,
            scale_mode=scale_mode,
            margin_mm=margin_mm,
            legend_position=legend_position,
            page_width_mm=page_width_mm,
            page_height_mm=page_height_mm,
            minimum_font_pt=minimum_font_pt,
            minimum_line_width_pt=minimum_line_width_pt,
            minimum_track_width_mm=minimum_track_width_mm,
            max_tracks_per_page=max_tracks_per_page,
            pages=tuple(pages),
            issues=tuple(issues),
            metadata={
                "page_count": len(pages),
                "legend_item_count": len(legend_items),
                "legend_reserved": legend_reserved,
                "source_width_px": source_width_px,
                "source_height_px": source_height_px,
                "source_width_pt": source_width_pt,
                "source_height_pt": source_height_pt,
                "printable_width_pt": printable_width,
                "printable_height_pt": printable_height,
                "content_scale": pages[0].content_scale if pages else 0.0,
                "page_track_counts": [len(page.track_ids) for page in pages],
                "paginated_track_count": sum(len(page.track_ids) for page in pages),
                "profile": profile.to_dict(),
                "multi_page_supported": True,
                "raw_dataframe_included": False,
                "ui_objects_included": False,
            },
        )

    def _paginate_tracks(
        self,
        tracks: list[dict[str, Any]],
        *,
        source_height_px: float,
        content_area: PrintRect,
        px_to_pt: float,
        scale_mode: str,
        minimum_track_width_mm: float,
        max_tracks_per_page: int,
    ) -> list[tuple[list[dict[str, Any]], PrintRect]]:
        if not tracks:
            return []
        groups: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        for track in tracks:
            candidate = [*current, track]
            if current and not _tracks_fit(
                candidate,
                source_height_px=source_height_px,
                content_area=content_area,
                px_to_pt=px_to_pt,
                scale_mode=scale_mode,
                minimum_track_width_mm=minimum_track_width_mm,
                max_tracks_per_page=max_tracks_per_page,
            ):
                groups.append(current)
                current = [track]
            else:
                current = candidate
        if current:
            groups.append(current)
        return [(group, _group_source_bounds(group, source_height_px)) for group in groups]


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in value] if isinstance(value, (list, tuple)) else []


def _print_tracks(layout: Mapping[str, Any]) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    for item in _mapping_list(layout.get("tracks")):
        bounds = item.get("bounds") if isinstance(item.get("bounds"), Mapping) else {}
        x = _non_negative_float(bounds.get("x"), -1.0)
        width = _positive_float(bounds.get("width"), 0.0)
        if x >= 0 and width > 0:
            tracks.append(dict(item))
    return sorted(tracks, key=lambda item: (_bounds_x(item), str(item.get("id") or "")))


def _bounds_x(track: Mapping[str, Any]) -> float:
    bounds = track.get("bounds") if isinstance(track.get("bounds"), Mapping) else {}
    return _non_negative_float(bounds.get("x"), 0.0)


def _bounds_width(track: Mapping[str, Any]) -> float:
    bounds = track.get("bounds") if isinstance(track.get("bounds"), Mapping) else {}
    return _positive_float(bounds.get("width"), 0.0)


def _group_source_bounds(group: list[dict[str, Any]], source_height_px: float) -> PrintRect:
    left = min(_bounds_x(item) for item in group)
    right = max(_bounds_x(item) + _bounds_width(item) for item in group)
    return PrintRect(left, 0.0, max(1.0, right - left), source_height_px)


def _content_scale(
    source_width_pt: float,
    source_height_pt: float,
    content_area: PrintRect,
    scale_mode: str,
) -> float:
    width_scale = content_area.width / max(source_width_pt, 1.0)
    height_scale = content_area.height / max(source_height_pt, 1.0)
    if scale_mode in {"actual_size", "fit_width", "fit_page"}:
        scale = min(1.0, width_scale, height_scale)
    else:  # defensive fallback; public validation normalizes the value
        scale = min(1.0, width_scale, height_scale)
    return max(0.01, scale)


def _tracks_fit(
    group: list[dict[str, Any]],
    *,
    source_height_px: float,
    content_area: PrintRect,
    px_to_pt: float,
    scale_mode: str,
    minimum_track_width_mm: float,
    max_tracks_per_page: int,
) -> bool:
    if len(group) > max_tracks_per_page:
        return False
    source = _group_source_bounds(group, source_height_px)
    scale = _content_scale(source.width * px_to_pt, source.height * px_to_pt, content_area, scale_mode)
    widths_mm = [(_bounds_width(item) * px_to_pt * scale) / MM_TO_PT for item in group]
    return bool(widths_mm) and min(widths_mm) + 1e-6 >= minimum_track_width_mm


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

