"""Validation helpers for renderer parity across Visualization Engine outputs.

The module compares a concrete renderer artifact with the renderer-neutral
``VisualizationRenderModel`` and ``VisualizationPrintLayout`` contracts.  It
contains no drawing code and can be reused by future SVG, PDF and HTML
renderers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VisualizationRendererParityReport:
    schema: str = "visualization.renderer.parity.report"
    version: str = "1.1"
    renderer: str = ""
    ok: bool = False
    expected_primitive_count: int = 0
    rendered_primitive_count: int = 0
    expected_clip_count: int = 0
    rendered_clip_count: int = 0
    print_layout_expected: bool = False
    print_layout_applied: bool = False
    expected_geometry_signature: str = ""
    rendered_geometry_signature: str = ""
    geometry_signature_match: bool = False
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "renderer": self.renderer,
            "ok": self.ok,
            "expected_primitive_count": self.expected_primitive_count,
            "rendered_primitive_count": self.rendered_primitive_count,
            "expected_clip_count": self.expected_clip_count,
            "rendered_clip_count": self.rendered_clip_count,
            "print_layout_expected": self.print_layout_expected,
            "print_layout_applied": self.print_layout_applied,
            "expected_geometry_signature": self.expected_geometry_signature,
            "rendered_geometry_signature": self.rendered_geometry_signature,
            "geometry_signature_match": self.geometry_signature_match,
            "issues": list(self.issues),
            "renderer_neutral": True,
        }


class VisualizationRendererParityValidator:
    """Compare a concrete renderer result with pipeline contracts."""

    def validate(
        self,
        pipeline: Mapping[str, Any],
        renderer_result: Mapping[str, Any],
    ) -> VisualizationRendererParityReport:
        render_model = _mapping(pipeline.get("render_model"))
        print_layout = _mapping(pipeline.get("print_layout"))
        primitives = [item for item in _mapping_list(render_model.get("primitives")) if _enabled(item)]
        clips = _mapping_list(render_model.get("clip_regions"))
        expected_primitive_count = len(primitives)
        expected_clip_count = len(clips)
        rendered_primitive_count = _non_negative_int(renderer_result.get("primitive_count"))
        rendered_clip_count = _non_negative_int(renderer_result.get("clip_count"))
        print_layout_expected = bool(print_layout.get("ok")) and bool(_mapping_list(print_layout.get("pages")))
        print_layout_applied = bool(renderer_result.get("print_layout_applied"))
        expected_geometry_signature = visualization_geometry_signature(pipeline)
        rendered_geometry_signature = str(renderer_result.get("geometry_signature") or "")
        geometry_signature_match = bool(expected_geometry_signature) and rendered_geometry_signature == expected_geometry_signature

        issues: list[str] = []
        if str(pipeline.get("schema") or "") != "visualization.scene.pipeline.result":
            issues.append("renderer_parity_unsupported_pipeline_schema")
        if str(render_model.get("schema") or "") != "visualization.render.model":
            issues.append("renderer_parity_render_model_missing")
        if rendered_primitive_count != expected_primitive_count:
            issues.append(
                f"renderer_parity_primitive_count_mismatch:{expected_primitive_count}:{rendered_primitive_count}"
            )
        if rendered_clip_count != expected_clip_count:
            issues.append(f"renderer_parity_clip_count_mismatch:{expected_clip_count}:{rendered_clip_count}")
        if print_layout_expected and not print_layout_applied:
            issues.append("renderer_parity_print_layout_not_applied")
        if not rendered_geometry_signature:
            issues.append("renderer_parity_geometry_signature_missing")
        elif not geometry_signature_match:
            issues.append("renderer_parity_geometry_signature_mismatch")
        if not bool(renderer_result.get("export_ready", False)) and expected_primitive_count:
            issues.append("renderer_parity_artifact_not_export_ready")

        return VisualizationRendererParityReport(
            renderer=str(renderer_result.get("renderer") or ""),
            ok=not issues,
            expected_primitive_count=expected_primitive_count,
            rendered_primitive_count=rendered_primitive_count,
            expected_clip_count=expected_clip_count,
            rendered_clip_count=rendered_clip_count,
            print_layout_expected=print_layout_expected,
            print_layout_applied=print_layout_applied,
            expected_geometry_signature=expected_geometry_signature,
            rendered_geometry_signature=rendered_geometry_signature,
            geometry_signature_match=geometry_signature_match,
            issues=tuple(issues),
        )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _enabled(item: Mapping[str, Any]) -> bool:
    return bool(item.get("visible", True)) and bool(item.get("printable", True))


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def visualization_geometry_signature(pipeline: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 signature for renderer-neutral geometry.

    The signature covers only printable primitive geometry, clip regions and all
    physical page transforms. Renderer-specific bytes, colorspaces and font
    embedding are intentionally excluded so SVG and PDF can be compared fairly.
    """

    render_model = _mapping(pipeline.get("render_model"))
    if str(render_model.get("schema") or "") != "visualization.render.model":
        return ""
    primitives = [_canonical_primitive(item) for item in _mapping_list(render_model.get("primitives")) if _enabled(item)]
    clips = [_canonical_clip(item) for item in _mapping_list(render_model.get("clip_regions"))]
    print_layout = _mapping(pipeline.get("print_layout"))
    pages = _mapping_list(print_layout.get("pages"))
    payload = {
        "schema": "visualization.geometry.signature/v2",
        "render_model_size": [_number(render_model.get("width")), _number(render_model.get("height"))],
        "primitives": primitives,
        "clip_regions": clips,
        "print": {
            "page_size": str(print_layout.get("page_size") or ""),
            "orientation": str(print_layout.get("orientation") or ""),
            "dpi": _number(print_layout.get("dpi")),
            "profile_id": str(print_layout.get("profile_id") or ""),
            "minimum_font_pt": _number(print_layout.get("minimum_font_pt")),
            "minimum_line_width_pt": _number(print_layout.get("minimum_line_width_pt")),
            "pages": [
                {
                    "index": int(page.get("index") or 0),
                    "page_bounds": _canonical_mapping(_mapping(page.get("page_bounds"))),
                    "content_bounds": _canonical_mapping(_mapping(page.get("content_bounds"))),
                    "source_bounds": _canonical_mapping(_mapping(page.get("source_bounds"))),
                    "content_scale": _number(page.get("content_scale")),
                    "track_ids": [str(item) for item in page.get("track_ids", [])],
                }
                for page in pages
            ],
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _canonical_primitive(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "kind": str(item.get("kind") or ""),
        "track_id": str(item.get("track_id") or ""),
        "clip_id": str(item.get("clip_id") or ""),
        "z_index": int(item.get("z_index") or 0),
        "payload": _canonical_mapping(_mapping(item.get("payload"))),
    }


def _canonical_clip(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "x": _number(item.get("x")),
        "y": _number(item.get("y")),
        "width": _number(item.get("width")),
        "height": _number(item.get("height")),
    }


def _canonical_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(str(k) for k in value.keys()):
        item = value.get(key)
        if isinstance(item, Mapping):
            result[key] = _canonical_mapping(item)
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            result[key] = [_canonical_value(v) for v in item]
        else:
            result[key] = _canonical_value(item)
    return result


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _canonical_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return _number(value)
    return str(value)


def _number(value: Any) -> float | int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    rounded = round(number, 6)
    return int(rounded) if rounded.is_integer() else rounded
