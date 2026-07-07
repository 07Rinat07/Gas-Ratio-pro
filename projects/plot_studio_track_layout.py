from __future__ import annotations

"""Professional track layout backend for Plot Studio 2.0.

The layout layer is renderer-independent.  It normalizes visible Plot Studio
tracks into a printable tablet layout: order, relative widths, pixel widths,
gutters, depth-track placement and frozen-track metadata.  It never mutates the
source PlotWorkspace or LAS/project data.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Literal

from projects.plot_studio_core import PlotRenderTrack, PlotWorkspace

DepthTrackPosition = Literal["left", "right", "hidden"]


@dataclass(frozen=True)
class PlotTrackLayoutConfig:
    """Visual layout settings used by Streamlit, exports and print engine."""

    canvas_width_px: int = 1200
    min_track_width_px: int = 90
    gutter_px: int = 8
    depth_track_width_px: int = 72
    depth_track_position: DepthTrackPosition = "left"
    freeze_depth_track: bool = True
    normalize_widths: bool = True


@dataclass(frozen=True)
class PlotTrackLayoutItem:
    """Renderer-ready geometry for one Plot Studio track."""

    track_id: str
    title: str
    order: int
    left_px: int
    width_px: int
    width_percent: float
    curve_count: int
    frozen: bool = False
    is_depth_track: bool = False

    @property
    def right_px(self) -> int:
        """Right edge in pixels, exclusive."""

        return self.left_px + self.width_px


@dataclass(frozen=True)
class PlotTrackLayoutResult:
    """Complete tablet layout manifest for Plot Studio tracks."""

    workspace_id: str
    canvas_width_px: int
    content_width_px: int
    gutter_px: int
    depth_track_position: DepthTrackPosition
    items: tuple[PlotTrackLayoutItem, ...]
    messages: tuple[str, ...] = ()

    @property
    def track_items(self) -> tuple[PlotTrackLayoutItem, ...]:
        return tuple(item for item in self.items if not item.is_depth_track)

    @property
    def total_width_px(self) -> int:
        if not self.items:
            return 0
        return max(item.right_px for item in self.items)


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


def _non_negative_int(value: Any, field_label: str) -> int:
    number = _finite_float(value, field_label)
    if number < 0:
        raise ValueError(f"{field_label}: значение не может быть отрицательным.")
    return int(round(number))


def validate_track_layout_config(config: PlotTrackLayoutConfig | None = None) -> PlotTrackLayoutConfig:
    """Validate and normalize layout configuration."""

    cfg = config or PlotTrackLayoutConfig()
    canvas_width = _positive_int(cfg.canvas_width_px, "Canvas width")
    min_track_width = _positive_int(cfg.min_track_width_px, "Minimum track width")
    gutter = _non_negative_int(cfg.gutter_px, "Track gutter")
    depth_width = _positive_int(cfg.depth_track_width_px, "Depth track width")
    position = str(cfg.depth_track_position or "left").strip().lower()
    if position not in {"left", "right", "hidden"}:
        raise ValueError("Depth track position: поддерживаются только left, right или hidden.")
    if canvas_width < min_track_width:
        raise ValueError("Canvas width: ширина холста меньше минимальной ширины трека.")
    return PlotTrackLayoutConfig(
        canvas_width_px=canvas_width,
        min_track_width_px=min_track_width,
        gutter_px=gutter,
        depth_track_width_px=depth_width,
        depth_track_position=position,  # type: ignore[arg-type]
        freeze_depth_track=bool(cfg.freeze_depth_track),
        normalize_widths=bool(cfg.normalize_widths),
    )


def _ordered_tracks(workspace: PlotWorkspace, track_order: Iterable[str] | None) -> tuple[PlotRenderTrack, ...]:
    tracks = tuple(workspace.tracks)
    if not track_order:
        return tracks
    requested = [str(track_id).strip() for track_id in track_order if str(track_id).strip()]
    priority = {track_id: index for index, track_id in enumerate(requested)}
    return tuple(sorted(tracks, key=lambda track: (priority.get(track.id, len(priority)), tracks.index(track))))


def _content_width(config: PlotTrackLayoutConfig, track_count: int) -> int:
    depth_width = 0 if config.depth_track_position == "hidden" else config.depth_track_width_px + config.gutter_px
    gutters = max(track_count - 1, 0) * config.gutter_px
    width = config.canvas_width_px - depth_width - gutters
    if track_count > 0 and width < track_count * config.min_track_width_px:
        width = track_count * config.min_track_width_px
    return max(width, 0)


def _track_widths_px(tracks: tuple[PlotRenderTrack, ...], content_width: int, config: PlotTrackLayoutConfig) -> tuple[int, ...]:
    if not tracks:
        return ()
    if not config.normalize_widths:
        widths = tuple(max(config.min_track_width_px, int(round(track.width))) for track in tracks)
        return widths
    total_weight = sum(max(_finite_float(track.width, "Track width"), 0.0) for track in tracks)
    if total_weight <= 0:
        total_weight = float(len(tracks))
        weights = [1.0 for _ in tracks]
    else:
        weights = [max(float(track.width), 0.0) for track in tracks]
    raw_widths = [max(config.min_track_width_px, int(round(content_width * weight / total_weight))) for weight in weights]
    diff = content_width - sum(raw_widths)
    if raw_widths:
        raw_widths[-1] = max(config.min_track_width_px, raw_widths[-1] + diff)
    return tuple(raw_widths)


def build_plot_track_layout(
    workspace: PlotWorkspace,
    *,
    config: PlotTrackLayoutConfig | None = None,
    track_order: Iterable[str] | None = None,
) -> PlotTrackLayoutResult:
    """Build a professional synchronized track layout for a PlotWorkspace."""

    cfg = validate_track_layout_config(config)
    tracks = _ordered_tracks(workspace, track_order)
    messages: list[str] = []
    if not tracks:
        messages.append("Нет видимых треков для раскладки Plot Studio.")

    content_width = _content_width(cfg, len(tracks))
    widths = _track_widths_px(tracks, content_width, cfg)
    items: list[PlotTrackLayoutItem] = []
    cursor = 0
    order = 0

    def append_depth_track() -> None:
        nonlocal cursor, order
        if cfg.depth_track_position == "hidden":
            return
        items.append(
            PlotTrackLayoutItem(
                track_id="__depth__",
                title="Depth",
                order=order,
                left_px=cursor,
                width_px=cfg.depth_track_width_px,
                width_percent=round(cfg.depth_track_width_px / max(cfg.canvas_width_px, 1) * 100, 2),
                curve_count=0,
                frozen=cfg.freeze_depth_track,
                is_depth_track=True,
            )
        )
        cursor += cfg.depth_track_width_px + cfg.gutter_px
        order += 1

    if cfg.depth_track_position == "left":
        append_depth_track()

    for index, track in enumerate(tracks):
        width_px = widths[index]
        items.append(
            PlotTrackLayoutItem(
                track_id=track.id,
                title=track.title,
                order=order,
                left_px=cursor,
                width_px=width_px,
                width_percent=round(width_px / max(cfg.canvas_width_px, 1) * 100, 2),
                curve_count=len(track.curves),
                frozen=False,
                is_depth_track=False,
            )
        )
        cursor += width_px + cfg.gutter_px
        order += 1

    if cfg.depth_track_position == "right":
        append_depth_track()

    if items and cursor >= cfg.gutter_px:
        cursor -= cfg.gutter_px

    return PlotTrackLayoutResult(
        workspace_id=workspace.template_id,
        canvas_width_px=max(cfg.canvas_width_px, cursor),
        content_width_px=content_width,
        gutter_px=cfg.gutter_px,
        depth_track_position=cfg.depth_track_position,
        items=tuple(items),
        messages=tuple(messages),
    )


def build_plot_track_layout_manifest(layout: PlotTrackLayoutResult) -> dict[str, Any]:
    """Return a JSON-serializable layout manifest for UI/export layers."""

    return {
        "workspace_id": layout.workspace_id,
        "canvas_width_px": layout.canvas_width_px,
        "content_width_px": layout.content_width_px,
        "gutter_px": layout.gutter_px,
        "depth_track_position": layout.depth_track_position,
        "total_width_px": layout.total_width_px,
        "items": [
            {
                "track_id": item.track_id,
                "title": item.title,
                "order": item.order,
                "left_px": item.left_px,
                "right_px": item.right_px,
                "width_px": item.width_px,
                "width_percent": item.width_percent,
                "curve_count": item.curve_count,
                "frozen": item.frozen,
                "is_depth_track": item.is_depth_track,
            }
            for item in layout.items
        ],
        "messages": list(layout.messages),
    }


def build_plot_track_layout_table(layout: PlotTrackLayoutResult) -> tuple[dict[str, Any], ...]:
    """Build compact table rows for Streamlit sidebars and diagnostics."""

    return tuple(
        {
            "Порядок": item.order,
            "Трек": item.title,
            "ID": item.track_id,
            "Left px": item.left_px,
            "Right px": item.right_px,
            "Width px": item.width_px,
            "Width %": item.width_percent,
            "Кривые": item.curve_count,
            "Закреплен": "да" if item.frozen else "нет",
            "Depth track": "да" if item.is_depth_track else "нет",
        }
        for item in layout.items
    )
