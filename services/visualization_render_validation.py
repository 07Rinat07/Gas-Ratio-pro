"""Renderer-neutral pre-render validation for Visualization Engine.

The validator runs after the shared Render Model is built and before concrete
SVG/PDF renderers consume it.  It verifies geometry safety, clip references,
page containment and high-level label collisions without importing any UI or
renderer implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VisualizationRenderValidationReport:
    schema: str = "visualization.render-validation.report"
    version: str = "1.0"
    ok: bool = False
    canvas_ok: bool = False
    clips_ok: bool = False
    primitives_ok: bool = False
    labels_ok: bool = False
    page_layout_ok: bool = False
    checked_primitive_count: int = 0
    checked_clip_count: int = 0
    checked_label_count: int = 0
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "ok": self.ok,
            "canvas_ok": self.canvas_ok,
            "clips_ok": self.clips_ok,
            "primitives_ok": self.primitives_ok,
            "labels_ok": self.labels_ok,
            "page_layout_ok": self.page_layout_ok,
            "checked_primitive_count": self.checked_primitive_count,
            "checked_clip_count": self.checked_clip_count,
            "checked_label_count": self.checked_label_count,
            "issues": list(self.issues),
            "renderer_neutral": True,
        }


class VisualizationRenderValidationPipeline:
    """Validate shared render geometry before concrete renderer execution."""

    TOLERANCE = 1e-6

    def validate(self, pipeline: Mapping[str, Any]) -> VisualizationRenderValidationReport:
        render_model = _mapping(pipeline.get("render_model"))
        print_layout = _mapping(pipeline.get("print_layout"))
        width = _positive(render_model.get("width"))
        height = _positive(render_model.get("height"))
        issues: list[str] = []

        canvas_ok = width > 0 and height > 0
        if str(render_model.get("schema") or "") != "visualization.render.model":
            issues.append("render_validation_render_model_missing")
            canvas_ok = False
        if not canvas_ok:
            issues.append("render_validation_canvas_invalid")

        canvas = (0.0, 0.0, width, height)
        clips = _mapping_list(render_model.get("clip_regions"))
        clip_bounds: dict[str, tuple[float, float, float, float]] = {}
        clip_issues: list[str] = []
        for clip in clips:
            clip_id = str(clip.get("id") or "")
            bounds = _rect_bounds(clip)
            if not clip_id:
                clip_issues.append("render_validation_clip_id_missing")
                continue
            if bounds is None:
                clip_issues.append(f"render_validation_clip_invalid:{clip_id}")
                continue
            if not _contains(canvas, bounds, self.TOLERANCE):
                clip_issues.append(f"render_validation_clip_outside_canvas:{clip_id}")
            clip_bounds[clip_id] = bounds
        issues.extend(clip_issues)

        primitives = [item for item in _mapping_list(render_model.get("primitives")) if _enabled(item)]
        primitive_issues: list[str] = []
        labels: list[tuple[str, str, tuple[float, float, float, float]]] = []
        for primitive in primitives:
            primitive_id = str(primitive.get("id") or "")
            kind = str(primitive.get("kind") or "")
            payload = _mapping(primitive.get("payload"))
            clip_id = str(primitive.get("clip_id") or "")
            bounds = _primitive_bounds(kind, payload)

            if not primitive_id:
                primitive_issues.append("render_validation_primitive_id_missing")
            if bounds is None:
                primitive_issues.append(f"render_validation_primitive_geometry_invalid:{primitive_id or kind}")
                continue
            if clip_id:
                clip = clip_bounds.get(clip_id)
                if clip is None:
                    primitive_issues.append(f"render_validation_missing_clip:{primitive_id}:{clip_id}")
                elif not _intersects(clip, bounds, self.TOLERANCE):
                    primitive_issues.append(f"render_validation_primitive_outside_clip:{primitive_id}:{clip_id}")
            elif not _contains(canvas, bounds, self.TOLERANCE):
                primitive_issues.append(f"render_validation_primitive_outside_canvas:{primitive_id}")

            if kind == "text":
                data_kind = str(payload.get("data_kind") or "")
                if data_kind in {"curve_label", "track_title"}:
                    labels.append((primitive_id, str(primitive.get("track_id") or ""), bounds))
        issues.extend(primitive_issues)

        label_issues: list[str] = []
        for index, (left_id, left_track, left_bounds) in enumerate(labels):
            for right_id, right_track, right_bounds in labels[index + 1 :]:
                if left_track and right_track and left_track != right_track:
                    continue
                if _overlap_area(left_bounds, right_bounds) > self.TOLERANCE:
                    label_issues.append(f"render_validation_label_overlap:{left_id}:{right_id}")
        issues.extend(label_issues)

        page_issues = self._validate_print_layout(print_layout, width, height)
        issues.extend(page_issues)

        unique_issues = tuple(dict.fromkeys(issues))
        return VisualizationRenderValidationReport(
            ok=not unique_issues,
            canvas_ok=canvas_ok,
            clips_ok=not clip_issues,
            primitives_ok=not primitive_issues,
            labels_ok=not label_issues,
            page_layout_ok=not page_issues,
            checked_primitive_count=len(primitives),
            checked_clip_count=len(clips),
            checked_label_count=len(labels),
            issues=unique_issues,
        )

    def _validate_print_layout(self, print_layout: Mapping[str, Any], width: float, height: float) -> list[str]:
        issues: list[str] = []
        if str(print_layout.get("schema") or "") != "visualization.print.layout":
            return ["render_validation_print_layout_missing"]
        pages = _mapping_list(print_layout.get("pages"))
        if not pages:
            return ["render_validation_print_pages_missing"]
        for page in pages:
            index = int(page.get("index") or 0)
            page_bounds = _rect_bounds(_mapping(page.get("page_bounds")))
            printable = _rect_bounds(_mapping(page.get("printable_bounds")))
            content = _rect_bounds(_mapping(page.get("content_bounds")))
            source = _rect_bounds(_mapping(page.get("source_bounds")))
            if page_bounds is None or printable is None or content is None or source is None:
                issues.append(f"render_validation_print_page_geometry_invalid:{index}")
                continue
            if not _contains(page_bounds, printable, self.TOLERANCE):
                issues.append(f"render_validation_printable_outside_page:{index}")
            if not _contains(printable, content, self.TOLERANCE):
                issues.append(f"render_validation_content_outside_printable:{index}")
            if not _close(source[2] - source[0], width) or not _close(source[3] - source[1], height):
                issues.append(f"render_validation_source_canvas_mismatch:{index}")
        return issues


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _enabled(item: Mapping[str, Any]) -> bool:
    return bool(item.get("visible", True)) and bool(item.get("printable", True))


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive(value: Any) -> float:
    number = _number(value)
    return number if number is not None and number > 0 else 0.0


def _rect_bounds(value: Mapping[str, Any]) -> tuple[float, float, float, float] | None:
    x = _number(value.get("x"))
    y = _number(value.get("y"))
    width = _number(value.get("width"))
    height = _number(value.get("height"))
    if x is None or y is None or width is None or height is None or width <= 0 or height <= 0:
        return None
    return x, y, x + width, y + height


def _primitive_bounds(kind: str, payload: Mapping[str, Any]) -> tuple[float, float, float, float] | None:
    if kind == "rectangle":
        return _rect_bounds(payload)
    if kind == "line":
        values = [_number(payload.get(key)) for key in ("x1", "y1", "x2", "y2")]
        if any(value is None for value in values):
            return None
        x1, y1, x2, y2 = (float(value) for value in values)
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
    if kind == "polyline":
        points = _mapping_list(payload.get("points"))
        coordinates = [(_number(point.get("x")), _number(point.get("y"))) for point in points]
        if len(coordinates) < 2 or any(x is None or y is None for x, y in coordinates):
            return None
        xs = [float(x) for x, _ in coordinates if x is not None]
        ys = [float(y) for _, y in coordinates if y is not None]
        return min(xs), min(ys), max(xs), max(ys)
    if kind == "text":
        x = _number(payload.get("x"))
        y = _number(payload.get("y"))
        size = _positive(payload.get("font_size"))
        text = str(payload.get("text") or "")
        if x is None or y is None or size <= 0 or not text:
            return None
        estimated_width = max(size * 0.55 * len(text), size * 0.55)
        anchor = str(payload.get("text_anchor") or "start")
        left = x - estimated_width / 2 if anchor == "middle" else x - estimated_width if anchor == "end" else x
        return left, y - size, left + estimated_width, y + size * 0.25
    return None


def _contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float], tolerance: float) -> bool:
    return (
        inner[0] >= outer[0] - tolerance
        and inner[1] >= outer[1] - tolerance
        and inner[2] <= outer[2] + tolerance
        and inner[3] <= outer[3] + tolerance
    )


def _intersects(left: tuple[float, float, float, float], right: tuple[float, float, float, float], tolerance: float) -> bool:
    return not (
        right[2] < left[0] - tolerance
        or right[0] > left[2] + tolerance
        or right[3] < left[1] - tolerance
        or right[1] > left[3] + tolerance
    )


def _overlap_area(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> float:
    width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return width * height


def _close(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return abs(left - right) <= tolerance
