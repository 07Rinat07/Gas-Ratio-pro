"""Validation helpers for renderer parity across Visualization Engine outputs.

The module compares a concrete renderer artifact with the renderer-neutral
``VisualizationRenderModel`` and ``VisualizationPrintLayout`` contracts.  It
contains no drawing code and can be reused by future SVG, PDF and HTML
renderers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class VisualizationRendererParityReport:
    schema: str = "visualization.renderer.parity.report"
    version: str = "1.0"
    renderer: str = ""
    ok: bool = False
    expected_primitive_count: int = 0
    rendered_primitive_count: int = 0
    expected_clip_count: int = 0
    rendered_clip_count: int = 0
    print_layout_expected: bool = False
    print_layout_applied: bool = False
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
