from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

PROJECT_PLOT_STUDIO_FILE_NAME = "plot_studio.json"
PLOT_AXIS_SCALES = {"linear", "log"}
PLOT_LINE_STYLES = {"solid", "dash", "dot", "dashdot"}
PLOT_EXPORT_FORMATS = {"pdf", "png", "svg"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _plot_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_PLOT_STUDIO_FILE_NAME


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_text(value: Any, field_label: str, *, max_length: int = 160, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_id(value: str, default: str = "item") -> str:
    raw = _clean_text(value, "ID", max_length=120) or default
    return safe_well_id(raw)


def _float_value(value: Any, field_label: str, *, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{field_label}: значение должно быть конечным числом.")
    return number


def _positive_float(value: Any, field_label: str, *, default: float) -> float:
    number = _float_value(value, field_label, default=default)
    assert number is not None
    if number <= 0:
        raise ValueError(f"{field_label}: значение должно быть больше нуля.")
    return number


def _clean_axis_scale(value: Any) -> str:
    scale = _clean_text(value, "Шкала оси", max_length=24).lower() or "linear"
    if scale not in PLOT_AXIS_SCALES:
        raise ValueError(f"Шкала оси должна быть одной из: {', '.join(sorted(PLOT_AXIS_SCALES))}.")
    return scale


def _clean_line_style(value: Any) -> str:
    style = _clean_text(value, "Стиль линии", max_length=24).lower() or "solid"
    if style not in PLOT_LINE_STYLES:
        raise ValueError(f"Стиль линии должен быть одним из: {', '.join(sorted(PLOT_LINE_STYLES))}.")
    return style


@dataclass(frozen=True)
class PlotAxisConfig:
    scale: str = "linear"
    min_value: float | None = None
    max_value: float | None = None
    inverted: bool = False
    auto_range: bool = True


@dataclass(frozen=True)
class PlotCurveConfig:
    id: str
    mnemonic: str
    track_id: str
    color: str = "#38bdf8"
    line_width: float = 1.4
    line_style: str = "solid"
    axis: PlotAxisConfig = field(default_factory=PlotAxisConfig)


@dataclass(frozen=True)
class PlotTrackConfig:
    id: str
    title: str
    width: float = 1.0
    visible: bool = True
    curve_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlotAnnotation:
    id: str
    text: str
    md_m: float
    track_id: str = ""
    annotation_type: str = "note"
    color: str = "#facc15"


@dataclass(frozen=True)
class PlotTemplate:
    id: str
    name: str
    well_id: str = ""
    tracks: tuple[PlotTrackConfig, ...] = ()
    curves: tuple[PlotCurveConfig, ...] = ()
    annotations: tuple[PlotAnnotation, ...] = ()
    grid_major_step: float = 100.0
    grid_minor_step: float = 20.0
    show_grid: bool = True
    export_formats: tuple[str, ...] = ("pdf", "png", "svg")
    updated_at: str = ""


@dataclass(frozen=True)
class PlotStudioSummary:
    templates: int
    tracks: int
    curves: int
    annotations: int
    export_formats: int


def _axis_from_dict(raw: dict[str, Any] | None) -> PlotAxisConfig:
    raw = raw if isinstance(raw, dict) else {}
    min_value = _float_value(raw.get("min_value"), "Минимум оси")
    max_value = _float_value(raw.get("max_value"), "Максимум оси")
    if min_value is not None and max_value is not None and min_value >= max_value:
        raise ValueError("Диапазон оси: минимум должен быть меньше максимума.")
    return PlotAxisConfig(
        scale=_clean_axis_scale(raw.get("scale", "linear")),
        min_value=min_value,
        max_value=max_value,
        inverted=bool(raw.get("inverted", False)),
        auto_range=bool(raw.get("auto_range", True)),
    )


def _axis_to_dict(axis: PlotAxisConfig) -> dict[str, Any]:
    return dict(axis.__dict__)


def _track_from_dict(raw: dict[str, Any]) -> PlotTrackConfig:
    return PlotTrackConfig(
        id=_safe_id(str(raw.get("id", "track")), "track"),
        title=_clean_text(raw.get("title"), "Название трека", required=True),
        width=_positive_float(raw.get("width", 1.0), "Ширина трека", default=1.0),
        visible=bool(raw.get("visible", True)),
        curve_ids=tuple(_safe_id(str(value), "curve") for value in raw.get("curve_ids", []) if str(value).strip()),
    )


def _track_to_dict(track: PlotTrackConfig) -> dict[str, Any]:
    return {**track.__dict__, "curve_ids": list(track.curve_ids)}


def _curve_from_dict(raw: dict[str, Any]) -> PlotCurveConfig:
    return PlotCurveConfig(
        id=_safe_id(str(raw.get("id", "curve")), "curve"),
        mnemonic=_clean_text(raw.get("mnemonic"), "Кривая", max_length=80, required=True).upper(),
        track_id=_safe_id(str(raw.get("track_id", "track-1")), "track"),
        color=_clean_text(raw.get("color", "#38bdf8"), "Цвет", max_length=32) or "#38bdf8",
        line_width=_positive_float(raw.get("line_width", 1.4), "Толщина линии", default=1.4),
        line_style=_clean_line_style(raw.get("line_style", "solid")),
        axis=_axis_from_dict(raw.get("axis")),
    )


def _curve_to_dict(curve: PlotCurveConfig) -> dict[str, Any]:
    return {**curve.__dict__, "axis": _axis_to_dict(curve.axis)}


def _annotation_from_dict(raw: dict[str, Any]) -> PlotAnnotation:
    md_m = _float_value(raw.get("md_m"), "Глубина аннотации")
    if md_m is None or md_m < 0 or md_m > 15000:
        raise ValueError("Глубина аннотации должна быть в диапазоне 0..15000 м.")
    return PlotAnnotation(
        id=_safe_id(str(raw.get("id", "annotation")), "annotation"),
        text=_clean_text(raw.get("text"), "Текст аннотации", max_length=240, required=True),
        md_m=md_m,
        track_id=_safe_id(str(raw.get("track_id", "")), "track") if raw.get("track_id") else "",
        annotation_type=_clean_text(raw.get("annotation_type", "note"), "Тип аннотации", max_length=40) or "note",
        color=_clean_text(raw.get("color", "#facc15"), "Цвет", max_length=32) or "#facc15",
    )


def _annotation_to_dict(annotation: PlotAnnotation) -> dict[str, Any]:
    return dict(annotation.__dict__)


def _template_from_dict(raw: dict[str, Any]) -> PlotTemplate:
    tracks = tuple(_track_from_dict(row) for row in raw.get("tracks", []) if isinstance(row, dict))
    curves = tuple(_curve_from_dict(row) for row in raw.get("curves", []) if isinstance(row, dict))
    annotations = tuple(_annotation_from_dict(row) for row in raw.get("annotations", []) if isinstance(row, dict))
    grid_major_step = _positive_float(raw.get("grid_major_step", 100.0), "Основная сетка", default=100.0)
    grid_minor_step = _positive_float(raw.get("grid_minor_step", 20.0), "Вспомогательная сетка", default=20.0)
    formats = tuple(str(value).lower().strip() for value in raw.get("export_formats", ("pdf", "png", "svg")) if str(value).strip())
    clean_formats = tuple(fmt for fmt in formats if fmt in PLOT_EXPORT_FORMATS) or ("pdf", "png", "svg")
    return PlotTemplate(
        id=_safe_id(str(raw.get("id", "template")), "template"),
        name=_clean_text(raw.get("name"), "Название шаблона", required=True),
        well_id=safe_well_id(str(raw.get("well_id", ""))) if raw.get("well_id") else "",
        tracks=tracks,
        curves=curves,
        annotations=annotations,
        grid_major_step=grid_major_step,
        grid_minor_step=grid_minor_step,
        show_grid=bool(raw.get("show_grid", True)),
        export_formats=clean_formats,
        updated_at=str(raw.get("updated_at", "")),
    )


def _template_to_dict(template: PlotTemplate) -> dict[str, Any]:
    return {
        "id": template.id,
        "name": template.name,
        "well_id": template.well_id,
        "tracks": [_track_to_dict(track) for track in template.tracks],
        "curves": [_curve_to_dict(curve) for curve in template.curves],
        "annotations": [_annotation_to_dict(annotation) for annotation in template.annotations],
        "grid_major_step": template.grid_major_step,
        "grid_minor_step": template.grid_minor_step,
        "show_grid": template.show_grid,
        "export_formats": list(template.export_formats),
        "updated_at": template.updated_at,
    }


def list_plot_templates(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[PlotTemplate, ...]:
    payload = _json_read(_plot_path(root, project_id), {"templates": []})
    rows = payload.get("templates", []) if isinstance(payload, dict) else []
    templates: list[PlotTemplate] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            templates.append(_template_from_dict(row))
        except ValueError:
            continue
    return tuple(sorted(templates, key=lambda item: item.updated_at, reverse=True))


def save_plot_template(
    root: Path | str,
    project_id: str,
    name: str,
    *,
    template_id: str | None = None,
    well_id: str = "",
    tracks: Iterable[PlotTrackConfig | dict[str, Any]] = (),
    curves: Iterable[PlotCurveConfig | dict[str, Any]] = (),
    annotations: Iterable[PlotAnnotation | dict[str, Any]] = (),
    grid_major_step: Any = 100.0,
    grid_minor_step: Any = 20.0,
    show_grid: bool = True,
    export_formats: Iterable[str] = ("pdf", "png", "svg"),
) -> PlotTemplate:
    clean_name = _clean_text(name, "Название шаблона", required=True)
    clean_id = _safe_id(template_id or f"plot-{clean_name.lower().replace(' ', '-')}", "plot")
    clean_tracks = tuple(item if isinstance(item, PlotTrackConfig) else _track_from_dict(item) for item in tracks)
    if not clean_tracks:
        clean_tracks = (
            PlotTrackConfig(id="track-depth", title="Depth", width=0.55),
            PlotTrackConfig(id="track-gamma", title="Gamma Ray", width=1.0),
            PlotTrackConfig(id="track-resistivity", title="Resistivity", width=1.0),
        )
    track_ids = {track.id for track in clean_tracks}
    clean_curves = tuple(item if isinstance(item, PlotCurveConfig) else _curve_from_dict(item) for item in curves)
    for curve in clean_curves:
        if curve.track_id not in track_ids:
            raise ValueError(f"Кривая {curve.mnemonic}: трек {curve.track_id} не найден.")
    clean_annotations = tuple(item if isinstance(item, PlotAnnotation) else _annotation_from_dict(item) for item in annotations)
    for annotation in clean_annotations:
        if annotation.track_id and annotation.track_id not in track_ids:
            raise ValueError(f"Аннотация {annotation.text}: трек {annotation.track_id} не найден.")
    formats = tuple(str(value).lower().strip() for value in export_formats if str(value).strip())
    invalid_formats = [fmt for fmt in formats if fmt not in PLOT_EXPORT_FORMATS]
    if invalid_formats:
        raise ValueError(f"Формат экспорта должен быть одним из: {', '.join(sorted(PLOT_EXPORT_FORMATS))}.")
    template = PlotTemplate(
        id=clean_id,
        name=clean_name,
        well_id=safe_well_id(well_id) if well_id else "",
        tracks=clean_tracks,
        curves=clean_curves,
        annotations=clean_annotations,
        grid_major_step=_positive_float(grid_major_step, "Основная сетка", default=100.0),
        grid_minor_step=_positive_float(grid_minor_step, "Вспомогательная сетка", default=20.0),
        show_grid=bool(show_grid),
        export_formats=formats or ("pdf", "png", "svg"),
        updated_at=_utc_now(),
    )
    existing = [item for item in list_plot_templates(root, project_id) if item.id != clean_id]
    _json_write(_plot_path(root, project_id), {"version": 1, "templates": [_template_to_dict(template), *[_template_to_dict(item) for item in existing]]})
    append_project_history(root, project_id, "plot-studio", f"Saved plot template {clean_name}", object_type="plot-template", object_id=clean_id)
    return template


def add_plot_track(root: Path | str, project_id: str, template_id: str, title: str, *, width: Any = 1.0, visible: bool = True, track_id: str | None = None) -> PlotTemplate:
    template = get_plot_template(root, project_id, template_id)
    new_track = PlotTrackConfig(id=_safe_id(track_id or f"track-{title.lower().replace(' ', '-')}", "track"), title=_clean_text(title, "Название трека", required=True), width=_positive_float(width, "Ширина трека", default=1.0), visible=visible)
    tracks = tuple(track for track in template.tracks if track.id != new_track.id) + (new_track,)
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=tracks, curves=template.curves, annotations=template.annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)


def add_plot_curve(root: Path | str, project_id: str, template_id: str, mnemonic: str, track_id: str, *, color: str = "#38bdf8", line_width: Any = 1.4, line_style: str = "solid", axis: PlotAxisConfig | dict[str, Any] | None = None, curve_id: str | None = None) -> PlotTemplate:
    template = get_plot_template(root, project_id, template_id)
    if track_id not in {track.id for track in template.tracks}:
        raise ValueError(f"Трек {track_id} не найден.")
    clean_mnemonic = _clean_text(mnemonic, "Кривая", max_length=80, required=True).upper()
    clean_id = _safe_id(curve_id or f"curve-{track_id}-{clean_mnemonic.lower()}", "curve")
    curve = PlotCurveConfig(id=clean_id, mnemonic=clean_mnemonic, track_id=_safe_id(track_id, "track"), color=_clean_text(color, "Цвет", max_length=32) or "#38bdf8", line_width=_positive_float(line_width, "Толщина линии", default=1.4), line_style=_clean_line_style(line_style), axis=axis if isinstance(axis, PlotAxisConfig) else _axis_from_dict(axis))
    curves = tuple(item for item in template.curves if item.id != clean_id) + (curve,)
    track_map = {track.id: track for track in template.tracks}
    updated_tracks = []
    for track in template.tracks:
        ids = tuple(value for value in track.curve_ids if value != clean_id)
        if track.id == curve.track_id:
            ids = ids + (clean_id,)
        updated_tracks.append(PlotTrackConfig(id=track.id, title=track.title, width=track.width, visible=track.visible, curve_ids=ids))
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=updated_tracks, curves=curves, annotations=template.annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)


def add_plot_annotation(root: Path | str, project_id: str, template_id: str, text: str, md_m: Any, *, track_id: str = "", annotation_type: str = "note", color: str = "#facc15", annotation_id: str | None = None) -> PlotTemplate:
    template = get_plot_template(root, project_id, template_id)
    if track_id and track_id not in {track.id for track in template.tracks}:
        raise ValueError(f"Трек {track_id} не найден.")
    annotation = _annotation_from_dict({"id": annotation_id or f"annotation-{text.lower().replace(' ', '-')}", "text": text, "md_m": md_m, "track_id": track_id, "annotation_type": annotation_type, "color": color})
    annotations = tuple(item for item in template.annotations if item.id != annotation.id) + (annotation,)
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=template.tracks, curves=template.curves, annotations=annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)



def remove_plot_track(root: Path | str, project_id: str, template_id: str, track_id: str, *, remove_curves: bool = True) -> PlotTemplate:
    """Remove a track from a plot template.

    By default curves assigned to the deleted track are removed as well. This keeps
    the template internally consistent and prevents hidden orphan curves from
    appearing during export or rendering.
    """
    template = get_plot_template(root, project_id, template_id)
    clean_track_id = _safe_id(track_id, "track")
    if clean_track_id not in {track.id for track in template.tracks}:
        raise ValueError(f"Трек {clean_track_id} не найден.")
    tracks = tuple(track for track in template.tracks if track.id != clean_track_id)
    if not tracks:
        raise ValueError("В шаблоне должен остаться хотя бы один трек.")
    if remove_curves:
        curves = tuple(curve for curve in template.curves if curve.track_id != clean_track_id)
    else:
        fallback_track_id = tracks[0].id
        curves = tuple(
            curve if curve.track_id != clean_track_id else PlotCurveConfig(
                id=curve.id,
                mnemonic=curve.mnemonic,
                track_id=fallback_track_id,
                color=curve.color,
                line_width=curve.line_width,
                line_style=curve.line_style,
                axis=curve.axis,
            )
            for curve in template.curves
        )
    cleaned_tracks = []
    curve_ids_by_track: dict[str, list[str]] = {track.id: [] for track in tracks}
    for curve in curves:
        curve_ids_by_track.setdefault(curve.track_id, []).append(curve.id)
    for track in tracks:
        cleaned_tracks.append(PlotTrackConfig(id=track.id, title=track.title, width=track.width, visible=track.visible, curve_ids=tuple(curve_ids_by_track.get(track.id, []))))
    annotations = tuple(annotation for annotation in template.annotations if annotation.track_id != clean_track_id)
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=cleaned_tracks, curves=curves, annotations=annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)


def reorder_plot_track(root: Path | str, project_id: str, template_id: str, track_id: str, direction: str) -> PlotTemplate:
    """Move a track left/right in the template order."""
    template = get_plot_template(root, project_id, template_id)
    clean_track_id = _safe_id(track_id, "track")
    tracks = list(template.tracks)
    index = next((idx for idx, track in enumerate(tracks) if track.id == clean_track_id), -1)
    if index < 0:
        raise ValueError(f"Трек {clean_track_id} не найден.")
    clean_direction = _clean_text(direction, "Направление", max_length=16).lower()
    if clean_direction in {"left", "up", "previous", "prev"}:
        target = max(0, index - 1)
    elif clean_direction in {"right", "down", "next"}:
        target = min(len(tracks) - 1, index + 1)
    else:
        raise ValueError("Направление должно быть left/up или right/down.")
    if target != index:
        tracks[index], tracks[target] = tracks[target], tracks[index]
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=tracks, curves=template.curves, annotations=template.annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)


def update_plot_track(root: Path | str, project_id: str, template_id: str, track_id: str, *, title: str | None = None, width: Any | None = None, visible: bool | None = None) -> PlotTemplate:
    """Update track title, width or visibility without changing curve assignment."""
    template = get_plot_template(root, project_id, template_id)
    clean_track_id = _safe_id(track_id, "track")
    updated: list[PlotTrackConfig] = []
    found = False
    for track in template.tracks:
        if track.id != clean_track_id:
            updated.append(track)
            continue
        found = True
        updated.append(PlotTrackConfig(
            id=track.id,
            title=_clean_text(title, "Название трека", required=True) if title is not None else track.title,
            width=_positive_float(width, "Ширина трека", default=track.width) if width is not None else track.width,
            visible=bool(visible) if visible is not None else track.visible,
            curve_ids=track.curve_ids,
        ))
    if not found:
        raise ValueError(f"Трек {clean_track_id} не найден.")
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=updated, curves=template.curves, annotations=template.annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)


def remove_plot_curve(root: Path | str, project_id: str, template_id: str, curve_id: str) -> PlotTemplate:
    """Remove a curve from a template and from its track curve list."""
    template = get_plot_template(root, project_id, template_id)
    clean_curve_id = _safe_id(curve_id, "curve")
    if clean_curve_id not in {curve.id for curve in template.curves}:
        raise ValueError(f"Кривая {clean_curve_id} не найдена.")
    curves = tuple(curve for curve in template.curves if curve.id != clean_curve_id)
    tracks = tuple(PlotTrackConfig(id=track.id, title=track.title, width=track.width, visible=track.visible, curve_ids=tuple(value for value in track.curve_ids if value != clean_curve_id)) for track in template.tracks)
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=tracks, curves=curves, annotations=template.annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)


def update_plot_curve(root: Path | str, project_id: str, template_id: str, curve_id: str, *, mnemonic: str | None = None, track_id: str | None = None, color: str | None = None, line_width: Any | None = None, line_style: str | None = None, axis: PlotAxisConfig | dict[str, Any] | None = None) -> PlotTemplate:
    """Update curve visual settings and optionally move it to another track."""
    template = get_plot_template(root, project_id, template_id)
    clean_curve_id = _safe_id(curve_id, "curve")
    track_ids = {track.id for track in template.tracks}
    updated_curves: list[PlotCurveConfig] = []
    found = False
    for curve in template.curves:
        if curve.id != clean_curve_id:
            updated_curves.append(curve)
            continue
        found = True
        next_track_id = _safe_id(track_id, "track") if track_id is not None else curve.track_id
        if next_track_id not in track_ids:
            raise ValueError(f"Трек {next_track_id} не найден.")
        updated_curves.append(PlotCurveConfig(
            id=curve.id,
            mnemonic=_clean_text(mnemonic, "Кривая", max_length=80, required=True).upper() if mnemonic is not None else curve.mnemonic,
            track_id=next_track_id,
            color=_clean_text(color, "Цвет", max_length=32) if color is not None else curve.color,
            line_width=_positive_float(line_width, "Толщина линии", default=curve.line_width) if line_width is not None else curve.line_width,
            line_style=_clean_line_style(line_style) if line_style is not None else curve.line_style,
            axis=axis if isinstance(axis, PlotAxisConfig) else (_axis_from_dict(axis) if axis is not None else curve.axis),
        ))
    if not found:
        raise ValueError(f"Кривая {clean_curve_id} не найдена.")
    curve_ids_by_track: dict[str, list[str]] = {track.id: [] for track in template.tracks}
    for curve in updated_curves:
        curve_ids_by_track.setdefault(curve.track_id, []).append(curve.id)
    tracks = tuple(PlotTrackConfig(id=track.id, title=track.title, width=track.width, visible=track.visible, curve_ids=tuple(curve_ids_by_track.get(track.id, []))) for track in template.tracks)
    return save_plot_template(root, project_id, template.name, template_id=template.id, well_id=template.well_id, tracks=tracks, curves=updated_curves, annotations=template.annotations, grid_major_step=template.grid_major_step, grid_minor_step=template.grid_minor_step, show_grid=template.show_grid, export_formats=template.export_formats)


def build_plot_export_manifest(template: PlotTemplate) -> dict[str, Any]:
    """Build a serializable export manifest for future PDF/PNG/SVG renderers."""
    visible_tracks = [track for track in template.tracks if track.visible]
    visible_track_ids = {track.id for track in visible_tracks}
    curves = [curve for curve in template.curves if curve.track_id in visible_track_ids]
    return {
        "template_id": template.id,
        "name": template.name,
        "well_id": template.well_id,
        "tracks": [_track_to_dict(track) for track in visible_tracks],
        "curves": [_curve_to_dict(curve) for curve in curves],
        "annotations": [_annotation_to_dict(annotation) for annotation in template.annotations if not annotation.track_id or annotation.track_id in visible_track_ids],
        "grid": {
            "enabled": template.show_grid,
            "major_step": template.grid_major_step,
            "minor_step": template.grid_minor_step,
        },
        "export_formats": list(template.export_formats),
        "updated_at": template.updated_at,
    }

def get_plot_template(root: Path | str, project_id: str, template_id: str) -> PlotTemplate:
    clean_id = _safe_id(template_id, "template")
    for template in list_plot_templates(root, project_id):
        if template.id == clean_id:
            return template
    raise FileNotFoundError(f"Plot template not found: {clean_id}")


def summarize_plot_studio(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> PlotStudioSummary:
    templates = list_plot_templates(root, project_id)
    return PlotStudioSummary(
        templates=len(templates),
        tracks=sum(len(template.tracks) for template in templates),
        curves=sum(len(template.curves) for template in templates),
        annotations=sum(len(template.annotations) for template in templates),
        export_formats=len({fmt for template in templates for fmt in template.export_formats}),
    )


def build_plot_studio_template_table(templates: Iterable[PlotTemplate]) -> list[dict[str, Any]]:
    return [
        {
            "Шаблон": template.name,
            "ID": template.id,
            "Скважина": template.well_id or "—",
            "Треки": len(template.tracks),
            "Кривые": len(template.curves),
            "Аннотации": len(template.annotations),
            "Сетка": "вкл" if template.show_grid else "выкл",
            "Экспорт": ", ".join(template.export_formats),
            "Обновлено": template.updated_at,
        }
        for template in templates
    ]


def build_plot_studio_track_table(template: PlotTemplate) -> list[dict[str, Any]]:
    curve_count = {track.id: 0 for track in template.tracks}
    for curve in template.curves:
        curve_count[curve.track_id] = curve_count.get(curve.track_id, 0) + 1
    return [
        {
            "Трек": track.title,
            "ID": track.id,
            "Ширина": track.width,
            "Виден": "да" if track.visible else "нет",
            "Кривые": curve_count.get(track.id, 0),
        }
        for track in template.tracks
    ]


def build_plot_studio_curve_table(template: PlotTemplate) -> list[dict[str, Any]]:
    return [
        {
            "Кривая": curve.mnemonic,
            "ID": curve.id,
            "Трек": curve.track_id,
            "Цвет": curve.color,
            "Толщина": curve.line_width,
            "Стиль": curve.line_style,
            "Шкала": curve.axis.scale,
            "Инверсия": "да" if curve.axis.inverted else "нет",
        }
        for curve in template.curves
    ]
