from __future__ import annotations

"""Renderer-independent Plot Studio annotation layer.

The module prepares depth markers, intervals, zones and text comments for Plot
Studio 2.0.  It works only with immutable PlotWorkspace/layout objects and does
not read or mutate original LAS data.  Renderers and export engines can consume
its manifest to draw annotations consistently on screen, in print and in export
artifacts.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Literal

from projects.plot_studio_core import PlotWorkspace
from projects.plot_studio_track_layout import (
    PlotTrackLayoutConfig,
    PlotTrackLayoutResult,
    build_plot_track_layout,
)

PlotAnnotationType = Literal["marker", "interval", "zone", "text"]
PLOT_ANNOTATION_TYPES: set[str] = {"marker", "interval", "zone", "text"}


@dataclass(frozen=True)
class PlotAnnotation:
    """User or interpretation annotation attached to a Plot Studio workspace."""

    id: str
    type: PlotAnnotationType
    depth_from: float
    depth_to: float | None = None
    track_id: str = ""
    label: str = ""
    text: str = ""
    color: str = "#ff9900"
    visible: bool = True
    locked: bool = False
    source: str = "manual"


@dataclass(frozen=True)
class PlotAnnotationPlacement:
    """Renderer-ready annotation geometry in pixel and depth coordinates."""

    annotation: PlotAnnotation
    clipped_depth_from: float
    clipped_depth_to: float | None
    y_from_px: int
    y_to_px: int | None
    left_px: int
    right_px: int
    track_id: str
    clipped: bool = False


@dataclass(frozen=True)
class PlotAnnotationLayerConfig:
    """Annotation preparation settings."""

    canvas_height_px: int = 1600
    top_margin_px: int = 80
    bottom_margin_px: int = 40
    show_hidden: bool = False
    include_locked: bool = True
    allow_global_annotations: bool = True


@dataclass(frozen=True)
class PlotAnnotationLayerResult:
    """Prepared annotation layer for UI, export and Operation Journal."""

    workspace_id: str
    workspace_name: str
    depth_from: float
    depth_to: float
    canvas_height_px: int
    plot_top_px: int
    plot_bottom_px: int
    placements: tuple[PlotAnnotationPlacement, ...]
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


def validate_annotation_layer_config(config: PlotAnnotationLayerConfig | None = None) -> PlotAnnotationLayerConfig:
    """Validate and normalize annotation layer settings."""

    cfg = config or PlotAnnotationLayerConfig()
    canvas_height = _positive_int(cfg.canvas_height_px, "Annotation canvas height")
    top_margin = int(round(_finite_float(cfg.top_margin_px, "Annotation top margin")))
    bottom_margin = int(round(_finite_float(cfg.bottom_margin_px, "Annotation bottom margin")))
    if top_margin < 0 or bottom_margin < 0:
        raise ValueError("Annotation margins: отступы не могут быть отрицательными.")
    if top_margin + bottom_margin >= canvas_height:
        raise ValueError("Annotation margins: сумма отступов должна быть меньше высоты canvas.")
    return PlotAnnotationLayerConfig(
        canvas_height_px=canvas_height,
        top_margin_px=top_margin,
        bottom_margin_px=bottom_margin,
        show_hidden=bool(cfg.show_hidden),
        include_locked=bool(cfg.include_locked),
        allow_global_annotations=bool(cfg.allow_global_annotations),
    )


def _clean_annotation(raw: PlotAnnotation) -> PlotAnnotation:
    annotation_id = str(raw.id).strip()
    if not annotation_id:
        raise ValueError("Annotation id: идентификатор аннотации обязателен.")
    annotation_type = str(raw.type).strip().lower()
    if annotation_type not in PLOT_ANNOTATION_TYPES:
        raise ValueError("Annotation type: поддерживаются marker, interval, zone и text.")
    depth_from = _finite_float(raw.depth_from, "Annotation depth_from")
    if depth_from < 0:
        raise ValueError("Annotation depth_from: глубина не может быть отрицательной.")
    depth_to = None if raw.depth_to is None else _finite_float(raw.depth_to, "Annotation depth_to")
    if depth_to is not None:
        if depth_to < 0:
            raise ValueError("Annotation depth_to: глубина не может быть отрицательной.")
        if depth_to < depth_from:
            raise ValueError("Annotation depth interval: depth_to должен быть больше или равен depth_from.")
    if annotation_type in {"interval", "zone"} and depth_to is None:
        raise ValueError("Annotation depth interval: для interval и zone требуется depth_to.")
    if annotation_type in {"marker", "text"}:
        depth_to = None
    label = str(raw.label or "").strip()
    text = str(raw.text or "").strip()
    if annotation_type in {"marker", "text"} and not label and not text:
        raise ValueError("Annotation label: для marker/text требуется label или text.")
    return PlotAnnotation(
        id=annotation_id,
        type=annotation_type,  # type: ignore[arg-type]
        depth_from=depth_from,
        depth_to=depth_to,
        track_id=str(raw.track_id or "").strip(),
        label=label,
        text=text,
        color=str(raw.color or "#ff9900").strip() or "#ff9900",
        visible=bool(raw.visible),
        locked=bool(raw.locked),
        source=str(raw.source or "manual").strip() or "manual",
    )


def validate_plot_annotations(annotations: Iterable[PlotAnnotation]) -> tuple[PlotAnnotation, ...]:
    """Validate annotation objects and protect against duplicate ids."""

    cleaned: list[PlotAnnotation] = []
    seen_ids: set[str] = set()
    for raw in annotations:
        annotation = _clean_annotation(raw)
        if annotation.id in seen_ids:
            raise ValueError(f"Annotation id: найден повторяющийся идентификатор {annotation.id}.")
        seen_ids.add(annotation.id)
        cleaned.append(annotation)
    return tuple(cleaned)


def _depth_to_y(depth: float, *, depth_from: float, depth_to: float, plot_top: int, plot_bottom: int) -> int:
    ratio = (depth - depth_from) / (depth_to - depth_from)
    return int(round(plot_top + ratio * (plot_bottom - plot_top)))


def _track_bounds(layout: PlotTrackLayoutResult) -> dict[str, tuple[int, int]]:
    return {item.track_id: (item.left_px, item.right_px) for item in layout.items}


def build_plot_annotation_layer(
    workspace: PlotWorkspace,
    annotations: Iterable[PlotAnnotation],
    *,
    layout: PlotTrackLayoutResult | None = None,
    layout_config: PlotTrackLayoutConfig | None = None,
    config: PlotAnnotationLayerConfig | None = None,
) -> PlotAnnotationLayerResult:
    """Build renderer-ready annotation placements for Plot Studio."""

    cfg = validate_annotation_layer_config(config)
    clean_annotations = validate_plot_annotations(annotations)
    actual_layout = layout or build_plot_track_layout(workspace, config=layout_config)
    track_bounds = _track_bounds(actual_layout)
    all_left = min((left for left, _right in track_bounds.values()), default=0)
    all_right = max((right for _left, right in track_bounds.values()), default=actual_layout.canvas_width_px)
    depth_from = workspace.viewport.depth_range.from_md
    depth_to = workspace.viewport.depth_range.to_md
    plot_top = cfg.top_margin_px
    plot_bottom = cfg.canvas_height_px - cfg.bottom_margin_px
    messages: list[str] = []
    placements: list[PlotAnnotationPlacement] = []

    for annotation in clean_annotations:
        if not annotation.visible and not cfg.show_hidden:
            messages.append(f"Annotation {annotation.id} hidden and skipped.")
            continue
        if annotation.locked and not cfg.include_locked:
            messages.append(f"Annotation {annotation.id} locked and skipped.")
            continue
        if annotation.track_id and annotation.track_id not in track_bounds:
            messages.append(f"Annotation {annotation.id} skipped: unknown track {annotation.track_id}.")
            continue
        if not annotation.track_id and not cfg.allow_global_annotations:
            messages.append(f"Annotation {annotation.id} skipped: global annotations disabled.")
            continue

        raw_to = annotation.depth_to if annotation.depth_to is not None else annotation.depth_from
        if raw_to < depth_from or annotation.depth_from > depth_to:
            messages.append(f"Annotation {annotation.id} outside viewport and skipped.")
            continue

        clipped_from = max(annotation.depth_from, depth_from)
        clipped_to = min(raw_to, depth_to)
        clipped = clipped_from != annotation.depth_from or clipped_to != raw_to
        y_from = _depth_to_y(clipped_from, depth_from=depth_from, depth_to=depth_to, plot_top=plot_top, plot_bottom=plot_bottom)
        y_to = None if annotation.depth_to is None else _depth_to_y(clipped_to, depth_from=depth_from, depth_to=depth_to, plot_top=plot_top, plot_bottom=plot_bottom)
        left, right = track_bounds.get(annotation.track_id, (all_left, all_right))
        placements.append(
            PlotAnnotationPlacement(
                annotation=annotation,
                clipped_depth_from=round(clipped_from, 6),
                clipped_depth_to=None if annotation.depth_to is None else round(clipped_to, 6),
                y_from_px=y_from,
                y_to_px=y_to,
                left_px=left,
                right_px=right,
                track_id=annotation.track_id,
                clipped=clipped,
            )
        )

    if not placements:
        messages.append("No visible annotations in current viewport.")
    return PlotAnnotationLayerResult(
        workspace_id=workspace.template_id,
        workspace_name=workspace.name,
        depth_from=depth_from,
        depth_to=depth_to,
        canvas_height_px=cfg.canvas_height_px,
        plot_top_px=plot_top,
        plot_bottom_px=plot_bottom,
        placements=tuple(placements),
        messages=tuple(messages),
    )


def build_plot_annotation_manifest(result: PlotAnnotationLayerResult) -> dict[str, Any]:
    """Serialize annotation layer for UI, export and Operation Journal."""

    return {
        "workspace_id": result.workspace_id,
        "workspace_name": result.workspace_name,
        "depth_from": result.depth_from,
        "depth_to": result.depth_to,
        "canvas_height_px": result.canvas_height_px,
        "plot_top_px": result.plot_top_px,
        "plot_bottom_px": result.plot_bottom_px,
        "placements": [
            {
                "id": placement.annotation.id,
                "type": placement.annotation.type,
                "track_id": placement.track_id,
                "label": placement.annotation.label,
                "text": placement.annotation.text,
                "color": placement.annotation.color,
                "visible": placement.annotation.visible,
                "locked": placement.annotation.locked,
                "source": placement.annotation.source,
                "depth_from": placement.annotation.depth_from,
                "depth_to": placement.annotation.depth_to,
                "clipped_depth_from": placement.clipped_depth_from,
                "clipped_depth_to": placement.clipped_depth_to,
                "y_from_px": placement.y_from_px,
                "y_to_px": placement.y_to_px,
                "left_px": placement.left_px,
                "right_px": placement.right_px,
                "clipped": placement.clipped,
            }
            for placement in result.placements
        ],
        "messages": list(result.messages),
    }


def build_plot_annotation_table(result: PlotAnnotationLayerResult) -> list[dict[str, Any]]:
    """Build compact table rows for Streamlit UI and debug panels."""

    return [
        {
            "id": placement.annotation.id,
            "type": placement.annotation.type,
            "track": placement.track_id or "ALL",
            "label": placement.annotation.label or placement.annotation.text,
            "depth_from": placement.clipped_depth_from,
            "depth_to": placement.clipped_depth_to,
            "y_from_px": placement.y_from_px,
            "y_to_px": placement.y_to_px,
            "clipped": placement.clipped,
        }
        for placement in result.placements
    ]
