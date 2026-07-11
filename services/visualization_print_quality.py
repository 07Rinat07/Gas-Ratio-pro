"""Renderer-neutral print quality validation for Visualization Engine.

The validator inspects the shared render model before concrete SVG/PDF output.
It checks engineering readability and geometry safety without drawing anything
or depending on a UI/rendering backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VisualizationPrintQualityReport:
    schema: str = "visualization.print-quality.report"
    version: str = "1.0"
    ok: bool = False
    primitive_count: int = 0
    curve_count: int = 0
    text_count: int = 0
    major_grid_count: int = 0
    minor_grid_count: int = 0
    minimum_font_size: float = 0.0
    minimum_curve_stroke_width: float = 0.0
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "ok": self.ok,
            "primitive_count": self.primitive_count,
            "curve_count": self.curve_count,
            "text_count": self.text_count,
            "major_grid_count": self.major_grid_count,
            "minor_grid_count": self.minor_grid_count,
            "minimum_font_size": self.minimum_font_size,
            "minimum_curve_stroke_width": self.minimum_curve_stroke_width,
            "issues": list(self.issues),
            "renderer_neutral": True,
        }


class VisualizationPrintQualityValidator:
    """Validate printable geometry and engineering readability."""

    MIN_FONT_SIZE = 7.0
    MIN_CURVE_STROKE_WIDTH = 0.6
    MAX_CURVE_STROKE_WIDTH = 4.0

    def validate(self, pipeline: Mapping[str, Any]) -> VisualizationPrintQualityReport:
        render_model = _mapping(pipeline.get("render_model"))
        primitives = [item for item in _mapping_list(render_model.get("primitives")) if _enabled(item)]
        clips = {str(item.get("id") or ""): item for item in _mapping_list(render_model.get("clip_regions"))}
        issues: list[str] = []
        curve_count = text_count = major_grid_count = minor_grid_count = 0
        font_sizes: list[float] = []
        curve_widths: list[float] = []
        curve_layer_ids: set[str] = set()
        curve_label_ids: set[str] = set()
        track_ids: set[str] = set()
        track_title_ids: set[str] = set()
        major_widths: list[float] = []
        minor_widths: list[float] = []

        if str(render_model.get("schema") or "") != "visualization.render.model":
            issues.append("print_quality_render_model_missing")

        for primitive in primitives:
            primitive_id = str(primitive.get("id") or "")
            kind = str(primitive.get("kind") or "")
            track_id = str(primitive.get("track_id") or "")
            clip_id = str(primitive.get("clip_id") or "")
            payload = _mapping(primitive.get("payload"))
            data_kind = str(payload.get("data_kind") or "")
            if track_id:
                track_ids.add(track_id)
            if clip_id and clip_id not in clips:
                issues.append(f"print_quality_missing_clip:{primitive_id}:{clip_id}")

            if kind == "polyline":
                points = _mapping_list(payload.get("points"))
                if len(points) < 2:
                    issues.append(f"print_quality_polyline_too_short:{primitive_id}")
                for index, point in enumerate(points):
                    if not _finite(point.get("x")) or not _finite(point.get("y")):
                        issues.append(f"print_quality_invalid_polyline_point:{primitive_id}:{index}")
                width = _positive(payload.get("stroke_width"))
                if data_kind == "curve":
                    curve_count += 1
                    curve_widths.append(width)
                    curve_layer_ids.add(str(payload.get("source_layer_id") or primitive_id))
                    if width < self.MIN_CURVE_STROKE_WIDTH:
                        issues.append(f"print_quality_curve_stroke_too_thin:{primitive_id}:{width:g}")
                    elif width > self.MAX_CURVE_STROKE_WIDTH:
                        issues.append(f"print_quality_curve_stroke_too_thick:{primitive_id}:{width:g}")

            elif kind == "text":
                text_count += 1
                text = str(payload.get("text") or "").strip()
                size = _positive(payload.get("font_size"))
                font_sizes.append(size)
                if not text:
                    issues.append(f"print_quality_empty_text:{primitive_id}")
                if size < self.MIN_FONT_SIZE:
                    issues.append(f"print_quality_font_too_small:{primitive_id}:{size:g}")
                if data_kind == "curve_label":
                    curve_label_ids.add(primitive_id.removeprefix("label."))
                if data_kind == "track_title":
                    track_title_ids.add(track_id or primitive_id.removeprefix("label.").removesuffix(".title"))

            elif kind == "line":
                for key in ("x1", "y1", "x2", "y2"):
                    if not _finite(payload.get(key)):
                        issues.append(f"print_quality_invalid_line_coordinate:{primitive_id}:{key}")
                if primitive_id.startswith("grid.depth."):
                    width = _positive(payload.get("stroke_width"))
                    if bool(payload.get("major")):
                        major_grid_count += 1
                        major_widths.append(width)
                    else:
                        minor_grid_count += 1
                        minor_widths.append(width)

            elif kind == "rectangle":
                for key in ("x", "y", "width", "height"):
                    if not _finite(payload.get(key)):
                        issues.append(f"print_quality_invalid_rectangle_coordinate:{primitive_id}:{key}")
                if _positive(payload.get("width")) <= 0 or _positive(payload.get("height")) <= 0:
                    issues.append(f"print_quality_invalid_rectangle_size:{primitive_id}")

        for layer_id in sorted(curve_layer_ids):
            if layer_id not in curve_label_ids:
                issues.append(f"print_quality_curve_label_missing:{layer_id}")
        for track_id in sorted(track_ids):
            if track_id and track_id not in track_title_ids:
                issues.append(f"print_quality_track_title_missing:{track_id}")
        if curve_count and not major_grid_count:
            issues.append("print_quality_major_depth_grid_missing")
        if major_widths and minor_widths and min(major_widths) <= max(minor_widths):
            issues.append("print_quality_grid_hierarchy_invalid")

        return VisualizationPrintQualityReport(
            ok=not issues,
            primitive_count=len(primitives),
            curve_count=curve_count,
            text_count=text_count,
            major_grid_count=major_grid_count,
            minor_grid_count=minor_grid_count,
            minimum_font_size=min(font_sizes) if font_sizes else 0.0,
            minimum_curve_stroke_width=min(curve_widths) if curve_widths else 0.0,
            issues=tuple(dict.fromkeys(issues)),
        )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _enabled(item: Mapping[str, Any]) -> bool:
    return bool(item.get("visible", True)) and bool(item.get("printable", True))


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _positive(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) and number > 0 else 0.0
