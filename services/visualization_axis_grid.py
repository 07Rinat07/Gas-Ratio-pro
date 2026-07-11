"""Renderer-neutral axis and grid contracts for Visualization Engine.

The module converts synchronized depth metadata and curve axis descriptors into
stable ticks and grid lines.  It performs geometry preparation only; concrete
renderers receive ready coordinates and do not calculate scales in UI code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class AxisTick:
    value: float
    position: float
    label: str = ""
    major: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "position": self.position,
            "label": self.label,
            "major": self.major,
        }


@dataclass(frozen=True, slots=True)
class AxisModel:
    id: str
    kind: str
    track_id: str
    orientation: str
    scale: str
    unit: str
    minimum: float
    maximum: float
    ticks: tuple[AxisTick, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "track_id": self.track_id,
            "orientation": self.orientation,
            "scale": self.scale,
            "unit": self.unit,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "ticks": [tick.to_dict() for tick in self.ticks],
        }


@dataclass(frozen=True, slots=True)
class GridLine:
    id: str
    track_id: str
    orientation: str
    position: float
    start: float
    stop: float
    major: bool
    axis_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "track_id": self.track_id,
            "orientation": self.orientation,
            "position": self.position,
            "start": self.start,
            "stop": self.stop,
            "major": self.major,
            "axis_id": self.axis_id,
        }


@dataclass(frozen=True, slots=True)
class VisualizationAxisGridModel:
    schema: str = "visualization.axis.grid.model"
    version: str = "1.0"
    axes: tuple[AxisModel, ...] = field(default_factory=tuple)
    grid_lines: tuple[GridLine, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.axes) and not any(issue.startswith("axis_grid_error:") for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "axes": [axis.to_dict() for axis in self.axes],
            "grid_lines": [line.to_dict() for line in self.grid_lines],
            "issues": list(self.issues),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationAxisGridEngine:
    """Build shared depth axes and per-curve horizontal axes."""

    DEPTH_MAJOR_INTERVALS = 5
    DEPTH_MINOR_DIVISIONS = 5
    CURVE_LINEAR_INTERVALS = 4

    def build(self, scene: Mapping[str, Any], layout: Mapping[str, Any]) -> VisualizationAxisGridModel:
        tracks = _mapping_list(scene.get("tracks"))
        layers = _mapping_list(scene.get("layers"))
        layout_tracks = _mapping_list(layout.get("tracks"))
        depth_layout = _mapping(layout.get("depth"))
        issues: list[str] = []
        axes: list[AxisModel] = []
        grid_lines: list[GridLine] = []

        start = _finite_float(depth_layout.get("start"))
        stop = _finite_float(depth_layout.get("stop"))
        plot_top = _finite_float(depth_layout.get("plot_top"))
        plot_bottom = _finite_float(depth_layout.get("plot_bottom"))
        if start is None or stop is None or stop <= start or plot_top is None or plot_bottom is None:
            issues.append("axis_grid_error:invalid_depth_layout")
        else:
            depth_ticks = self._depth_ticks(start, stop, plot_top, plot_bottom)
            depth_axis = AxisModel(
                id="axis.depth.shared",
                kind="depth",
                track_id="",
                orientation="vertical",
                scale="linear",
                unit=str(depth_layout.get("unit") or ""),
                minimum=start,
                maximum=stop,
                ticks=depth_ticks,
            )
            axes.append(depth_axis)
            for track_layout in layout_tracks:
                track_id = str(track_layout.get("id") or "")
                plot = _mapping(track_layout.get("plot_bounds"))
                x = _number(plot.get("x"))
                width = _non_negative(plot.get("width"))
                for index, tick in enumerate(depth_ticks):
                    grid_lines.append(
                        GridLine(
                            id=f"grid.depth.{track_id}.{index}",
                            track_id=track_id,
                            orientation="horizontal",
                            position=tick.position,
                            start=x,
                            stop=x + width,
                            major=tick.major,
                            axis_id=depth_axis.id,
                        )
                    )

        layout_by_id = {str(item.get("id") or ""): item for item in layout_tracks}
        for track in tracks:
            track_id = str(track.get("id") or "")
            track_layout = _mapping(layout_by_id.get(track_id))
            plot = _mapping(track_layout.get("plot_bounds"))
            axis_bounds = _mapping(track_layout.get("axis_bounds"))
            x = _number(plot.get("x"))
            width = _non_negative(plot.get("width"))
            y1 = _number(plot.get("y"))
            y2 = y1 + _non_negative(plot.get("height"))
            curve_layers = [
                layer for layer in layers
                if str(layer.get("track_id") or "") == track_id and str(layer.get("kind") or "") == "curve"
            ]
            for curve_index, layer in enumerate(curve_layers):
                payload = _mapping(layer.get("payload"))
                axis_desc = _mapping(payload.get("axis"))
                minimum = _finite_float(axis_desc.get("min"))
                maximum = _finite_float(axis_desc.get("max"))
                if minimum is None or maximum is None or maximum <= minimum:
                    issues.append(f"axis_grid_curve_axis_invalid:{layer.get('id', '')}".rstrip(":"))
                    continue
                scale = str(axis_desc.get("scale") or "linear").lower()
                ticks = self._curve_ticks(minimum, maximum, x, x + width, scale)
                axis_id = f"axis.curve.{str(layer.get('id') or curve_index)}"
                axes.append(
                    AxisModel(
                        id=axis_id,
                        kind="curve",
                        track_id=track_id,
                        orientation="horizontal",
                        scale=scale,
                        unit=str(payload.get("unit") or ""),
                        minimum=minimum,
                        maximum=maximum,
                        ticks=ticks,
                    )
                )
                for tick_index, tick in enumerate(ticks):
                    grid_lines.append(
                        GridLine(
                            id=f"grid.curve.{track_id}.{curve_index}.{tick_index}",
                            track_id=track_id,
                            orientation="vertical",
                            position=tick.position,
                            start=y1,
                            stop=y2,
                            major=tick.major,
                            axis_id=axis_id,
                        )
                    )
                if not axis_bounds:
                    issues.append(f"axis_grid_missing_axis_bounds:{track_id}")

        if not tracks:
            issues.append("axis_grid_error:no_tracks")
        return VisualizationAxisGridModel(
            axes=tuple(sorted(axes, key=lambda item: (item.kind, item.track_id, item.id))),
            grid_lines=tuple(sorted(grid_lines, key=lambda item: (item.track_id, item.orientation, item.position, item.id))),
            issues=tuple(dict.fromkeys(issues)),
        )

    def _depth_ticks(self, start: float, stop: float, top: float, bottom: float) -> tuple[AxisTick, ...]:
        major_step = _nice_step((stop - start) / self.DEPTH_MAJOR_INTERVALS)
        minor_step = major_step / self.DEPTH_MINOR_DIVISIONS
        first = math.ceil(start / minor_step) * minor_step
        ticks: list[AxisTick] = []
        value = first
        guard = 0
        while value <= stop + 1e-9 and guard < 500:
            bounded_value = min(max(value, start), stop)
            ratio = (bounded_value - start) / (stop - start)
            position = top + ratio * (bottom - top)
            major = _is_multiple(bounded_value, major_step)
            ticks.append(AxisTick(value=bounded_value, position=position, label=_format_value(bounded_value) if major else "", major=major))
            value += minor_step
            guard += 1
        return tuple(ticks)

    def _curve_ticks(self, minimum: float, maximum: float, left: float, right: float, scale: str) -> tuple[AxisTick, ...]:
        if scale == "log" and minimum > 0 and maximum > 0:
            start_exp = math.floor(math.log10(minimum))
            stop_exp = math.ceil(math.log10(maximum))
            ticks: list[AxisTick] = []
            log_min = math.log10(minimum)
            log_max = math.log10(maximum)
            for exponent in range(start_exp, stop_exp + 1):
                for multiplier in range(1, 10):
                    value = multiplier * (10 ** exponent)
                    if value < minimum or value > maximum:
                        continue
                    position = left + ((math.log10(value) - log_min) / (log_max - log_min)) * (right - left)
                    major = multiplier == 1
                    ticks.append(AxisTick(value=value, position=position, label=_format_value(value) if major else "", major=major))
            return tuple(ticks)

        step = _nice_step((maximum - minimum) / self.CURVE_LINEAR_INTERVALS)
        first = math.ceil(minimum / step) * step
        values = [minimum]
        value = first
        while value < maximum and len(values) < 100:
            if value > minimum + step * 0.1:
                values.append(value)
            value += step
        values.append(maximum)
        unique = sorted(set(round(item, 12) for item in values))
        return tuple(
            AxisTick(
                value=item,
                position=left + ((item - minimum) / (maximum - minimum)) * (right - left),
                label=_format_value(item),
                major=True,
            )
            for item in unique
        )


def _nice_step(raw: float) -> float:
    if raw <= 0 or not math.isfinite(raw):
        return 1.0
    exponent = math.floor(math.log10(raw))
    fraction = raw / (10 ** exponent)
    if fraction <= 1:
        nice = 1
    elif fraction <= 2:
        nice = 2
    elif fraction <= 5:
        nice = 5
    else:
        nice = 10
    return nice * (10 ** exponent)


def _is_multiple(value: float, step: float) -> bool:
    quotient = value / step
    return abs(quotient - round(quotient)) < 1e-7


def _format_value(value: float) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 10000 or magnitude < 0.01:
        return f"{value:.2g}"
    if abs(value - round(value)) < 1e-8:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [_mapping(item) for item in _sequence(value) if isinstance(item, Mapping)]


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _number(value: Any) -> float:
    parsed = _finite_float(value)
    return parsed if parsed is not None else 0.0


def _non_negative(value: Any) -> float:
    return max(0.0, _number(value))
