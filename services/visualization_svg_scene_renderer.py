"""Printable SVG renderer for Visualization Engine scene contracts.

The adapter consumes ``VisualizationScenePipelineResult`` dictionaries (or a
plain ``visualization.engine.scene`` mapping) and produces a deterministic SVG
artifact.  It does not parse LAS files and does not perform interpretation
calculations: all curves, overlays, axes and synchronized depth metadata must
already be present in the scene contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
import math
from typing import Any, Mapping, Sequence

from services.visualization_renderer_parity import visualization_geometry_signature
from services.visualization_render_validation import validate_export_source


@dataclass(frozen=True, slots=True)
class SvgSceneRenderResult:
    """Serializable output of the scene-to-SVG adapter."""

    schema: str = "visualization.renderer.svg.result"
    version: str = "1.1"
    renderer: str = "visualization_svg_scene_renderer"
    source_schema: str = ""
    width: int = 0
    height: int = 0
    track_count: int = 0
    layer_count: int = 0
    curve_count: int = 0
    overlay_count: int = 0
    primitive_count: int = 0
    clip_count: int = 0
    print_layout_applied: bool = False
    page_size: str = ""
    page_count: int = 0
    geometry_signature: str = ""
    export_ready: bool = False
    issues: tuple[str, ...] = field(default_factory=tuple)
    svg: str = ""
    page_svgs: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "renderer": self.renderer,
            "source_schema": self.source_schema,
            "format": "svg",
            "width": self.width,
            "height": self.height,
            "track_count": self.track_count,
            "layer_count": self.layer_count,
            "curve_count": self.curve_count,
            "overlay_count": self.overlay_count,
            "primitive_count": self.primitive_count,
            "clip_count": self.clip_count,
            "print_layout_applied": self.print_layout_applied,
            "page_size": self.page_size,
            "page_count": self.page_count,
            "geometry_signature": self.geometry_signature,
            "export_ready": self.export_ready,
            "contains_raw_dataframe": False,
            "issues": list(self.issues),
            "svg": self.svg,
            "page_svgs": list(self.page_svgs),
        }


class VisualizationSvgSceneRenderer:
    """Render a printable SVG directly from a Visualization Engine scene."""

    DEFAULT_TRACK_WIDTH = 180
    MIN_TRACK_WIDTH = 120
    HEADER_HEIGHT = 42
    AXIS_HEIGHT = 22
    FOOTER_HEIGHT = 24
    PLOT_HEIGHT = 620
    SIDE_PADDING = 12

    def render(self, source: Mapping[str, Any]) -> SvgSceneRenderResult:
        scene, layout, source_schema, upstream_issues = self._extract_scene(source)
        tracks = _mapping_list(scene.get("tracks"))
        layers = _mapping_list(scene.get("layers"))
        depth_sync = _mapping(scene.get("depth_sync"))
        render_model = _mapping(source.get("render_model")) if source_schema == "visualization.scene.pipeline.result" else {}
        print_layout = _mapping(source.get("print_layout")) if source_schema == "visualization.scene.pipeline.result" else {}

        issues = list(upstream_issues)
        if source_schema == "visualization.scene.pipeline.result":
            validation_report = validate_export_source(source)
            if not validation_report.export_allowed:
                issues.append("svg_renderer_blocked_by_render_validation")
                issues.extend(f"svg_renderer_validation:{item.code}" for item in validation_report.findings if item.blocking)
                return SvgSceneRenderResult(
                    source_schema=source_schema,
                    width=int(_positive_float(render_model.get("width"), 0)),
                    height=int(_positive_float(render_model.get("height"), 0)),
                    track_count=len(tracks),
                    layer_count=len(layers),
                    curve_count=sum(1 for layer in layers if str(layer.get("kind")) == "curve"),
                    overlay_count=sum(1 for layer in layers if str(layer.get("kind")) == "interval_overlay"),
                    primitive_count=len([item for item in _mapping_list(render_model.get("primitives")) if bool(item.get("visible", True)) and bool(item.get("printable", True))]),
                    clip_count=len(_mapping_list(render_model.get("clip_regions"))),
                    page_size=str(print_layout.get("page_size") or ""),
                    geometry_signature=visualization_geometry_signature(source),
                    export_ready=False,
                    issues=tuple(dict.fromkeys(issues)),
                    svg="",
                )
        if not tracks:
            issues.append("svg_renderer_scene_has_no_tracks")
        if not layers:
            issues.append("svg_renderer_scene_has_no_layers")

        depth_start = _finite_float(depth_sync.get("start"))
        depth_stop = _finite_float(depth_sync.get("stop"))
        if depth_start is None or depth_stop is None or depth_stop <= depth_start:
            issues.append("svg_renderer_invalid_depth_domain")

        layout_tracks = _mapping_list(layout.get("tracks"))
        layout_by_track = {str(item.get("id") or ""): item for item in layout_tracks}
        width = int(_positive_float(layout.get("width"), 0))
        height = int(_positive_float(layout.get("height"), 0))
        if not width or not height or len(layout_tracks) != len(tracks):
            issues.append("svg_renderer_missing_layout_contract")
            track_widths = [
                max(self.MIN_TRACK_WIDTH, int(self.DEFAULT_TRACK_WIDTH * max(_positive_float(track.get("width"), 1.0), 0.5)))
                for track in tracks
            ]
            width = max(360, sum(track_widths) + self.SIDE_PADDING * 2)
            height = self.HEADER_HEIGHT + self.AXIS_HEIGHT + self.PLOT_HEIGHT + self.FOOTER_HEIGHT
        else:
            track_widths = [int(_mapping(layout_by_track.get(str(track.get("id") or ""))).get("plot_bounds", {}).get("width") or self.DEFAULT_TRACK_WIDTH) for track in tracks]

        layer_by_track: dict[str, list[dict[str, Any]]] = {}
        for layer in layers:
            if not bool(layer.get("visible", True)) or not bool(layer.get("printable", True)):
                continue
            layer_by_track.setdefault(str(layer.get("track_id") or ""), []).append(layer)
        for values in layer_by_track.values():
            values.sort(key=lambda item: (int(item.get("z_index") or 0), str(item.get("id") or "")))

        primitive_count = 0
        clip_count = 0
        print_layout_applied = False
        page_size = ""
        page_count = 0
        page_svgs: tuple[str, ...] = ()
        if render_model.get("schema") == "visualization.render.model" and _mapping_list(render_model.get("primitives")):
            width = int(_positive_float(render_model.get("width"), width))
            height = int(_positive_float(render_model.get("height"), height))
            primitive_count = len([item for item in _mapping_list(render_model.get("primitives")) if bool(item.get("visible", True)) and bool(item.get("printable", True))])
            clip_count = len(_mapping_list(render_model.get("clip_regions")))
            page = _mapping((_mapping_list(print_layout.get("pages")) or [{}])[0])
            page_bounds = _mapping(page.get("page_bounds"))
            if bool(print_layout.get("ok")) and page_bounds:
                width = int(round(_positive_float(page_bounds.get("width"), width)))
                height = int(round(_positive_float(page_bounds.get("height"), height)))
                print_layout_applied = True
                page_size = str(print_layout.get("page_size") or "")
            pages = _mapping_list(print_layout.get("pages")) if print_layout_applied else []
            if pages:
                rendered_pages: list[str] = []
                for page in pages:
                    bounds = _mapping(page.get("page_bounds"))
                    page_width = int(round(_positive_float(bounds.get("width"), width)))
                    page_height = int(round(_positive_float(bounds.get("height"), height)))
                    rendered_pages.append(
                        self._render_from_render_model(
                            render_model,
                            width=page_width,
                            height=page_height,
                            issues=issues,
                            print_layout=print_layout,
                            page=page,
                        )
                    )
                page_svgs = tuple(rendered_pages)
            else:
                page_svgs = (
                    self._render_from_render_model(
                        render_model,
                        width=width,
                        height=height,
                        issues=issues,
                        print_layout=print_layout,
                    ),
                )
            page_count = len(page_svgs)
            svg = page_svgs[0]
        else:
            issues.append("svg_renderer_render_model_unavailable")
            svg = self._render_svg(
                tracks=tracks,
                layer_by_track=layer_by_track,
                depth_sync=depth_sync,
                depth_start=depth_start,
                depth_stop=depth_stop,
                track_widths=track_widths,
                layout_by_track=layout_by_track,
                width=width,
                height=height,
                issues=issues,
            )
            page_svgs = (svg,)
            page_count = 1
        curve_count = sum(1 for layer in layers if str(layer.get("kind")) == "curve")
        overlay_count = sum(1 for layer in layers if str(layer.get("kind")) == "interval_overlay")
        export_ready = bool(tracks and curve_count and depth_start is not None and depth_stop is not None and depth_stop > depth_start)
        geometry_signature = visualization_geometry_signature(source) if source_schema == "visualization.scene.pipeline.result" else ""
        return SvgSceneRenderResult(
            source_schema=source_schema,
            width=width,
            height=height,
            track_count=len(tracks),
            layer_count=len(layers),
            curve_count=curve_count,
            overlay_count=overlay_count,
            primitive_count=primitive_count,
            clip_count=clip_count,
            print_layout_applied=print_layout_applied,
            page_size=page_size,
            page_count=page_count,
            geometry_signature=geometry_signature,
            export_ready=export_ready,
            issues=tuple(dict.fromkeys(issues)),
            svg=svg,
            page_svgs=page_svgs,
        )


    def _render_from_render_model(
        self,
        render_model: Mapping[str, Any],
        *,
        width: int,
        height: int,
        issues: list[str],
        print_layout: Mapping[str, Any] | None = None,
        page: Mapping[str, Any] | None = None,
    ) -> str:
        clips = _mapping_list(render_model.get("clip_regions"))
        primitives = _mapping_list(render_model.get("primitives"))
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}pt" height="{height}pt" viewBox="0 0 {width} {height}" role="img" aria-label="LAS visualization">',
            '<defs>',
        ]
        for clip in clips:
            clip_id = escape(str(clip.get("id") or ""), quote=True)
            if not clip_id:
                continue
            parts.append(
                f'<clipPath id="{clip_id}"><rect x="{_finite_float(clip.get("x")) or 0:g}" '
                f'y="{_finite_float(clip.get("y")) or 0:g}" width="{_positive_float(clip.get("width"), 0):g}" '
                f'height="{_positive_float(clip.get("height"), 0):g}"/></clipPath>'
            )
        selected_page = dict(page or {})
        content = _mapping(selected_page.get("content_bounds"))
        page_clip_id = "print-page-content"
        if content:
            parts.append(
                f'<clipPath id="{page_clip_id}" clipPathUnits="userSpaceOnUse"><rect '
                f'x="{_number(content.get("x"))}" y="{_number(content.get("y"))}" '
                f'width="{_number(content.get("width"))}" height="{_number(content.get("height"))}"/></clipPath>'
            )
        parts.append('</defs>')
        if content:
            parts.append(f'<g clip-path="url(#{page_clip_id})">')
        transform, physical_scale = self._print_transform(print_layout or {}, render_model, selected_page)
        minimum_font_pt = _positive_float((print_layout or {}).get("minimum_font_pt"), 1.0)
        minimum_line_width_pt = _positive_float((print_layout or {}).get("minimum_line_width_pt"), 0.1)
        page_track_ids = _string_set(selected_page.get("track_ids"))
        parts.append(f'<g font-family="Arial, DejaVu Sans, sans-serif"{transform}>')
        for primitive in primitives:
            if (
                not bool(primitive.get("visible", True))
                or not bool(primitive.get("printable", True))
                or not _primitive_on_page(primitive, page_track_ids)
            ):
                continue
            payload = _mapping(primitive.get("payload"))
            kind = str(primitive.get("kind") or "")
            primitive_id = escape(str(primitive.get("id") or ""), quote=True)
            track_id = escape(str(primitive.get("track_id") or ""), quote=True)
            clip_id = escape(str(primitive.get("clip_id") or ""), quote=True)
            attrs = f' data-primitive="{primitive_id}"'
            if track_id:
                attrs += f' data-track="{track_id}"'
            data_kind = escape(str(payload.get("data_kind") or ""), quote=True)
            if data_kind:
                attrs += f' data-kind="{data_kind}"'
            if clip_id:
                attrs += f' clip-path="url(#{clip_id})"'
            if kind == "rectangle":
                stroke_width = max(minimum_line_width_pt, _positive_float(payload.get("stroke_width"), 1.0))
                parts.append(
                    f'<rect{attrs} x="{_number(payload.get("x"))}" y="{_number(payload.get("y"))}" '
                    f'width="{_number(payload.get("width"))}" height="{_number(payload.get("height"))}" '
                    f'fill="{_safe_color_or_none(payload.get("fill"), "none")}" stroke="{_safe_color_or_none(payload.get("stroke"), "none")}" '
                    f'stroke-width="{stroke_width:g}" vector-effect="non-scaling-stroke" fill-opacity="{_number(payload.get("fill_opacity"), 1)}" '
                    f'stroke-opacity="{_number(payload.get("stroke_opacity"), 1)}" rx="{_number(payload.get("corner_radius"), 0)}"/>'
                )
            elif kind == "line":
                stroke_width = max(minimum_line_width_pt, _positive_float(payload.get("stroke_width"), 1.0))
                parts.append(
                    f'<line{attrs} x1="{_number(payload.get("x1"))}" y1="{_number(payload.get("y1"))}" '
                    f'x2="{_number(payload.get("x2"))}" y2="{_number(payload.get("y2"))}" '
                    f'stroke="{_safe_color_or_none(payload.get("stroke"), "#607d8b")}" stroke-width="{stroke_width:g}" vector-effect="non-scaling-stroke"/>'
                )
            elif kind == "text":
                text = escape(str(payload.get("text") or ""))
                anchor = escape(str(payload.get("text_anchor") or "start"), quote=True)
                font_size = max(
                    _positive_float(payload.get("font_size"), 10.0),
                    minimum_font_pt / max(physical_scale, 0.01),
                )
                parts.append(
                    f'<text{attrs} x="{_number(payload.get("x"))}" y="{_number(payload.get("y"))}" '
                    f'font-size="{font_size:g}" font-weight="{_number(payload.get("font_weight"), 400)}" '
                    f'text-anchor="{anchor}" fill="{_safe_color_or_none(payload.get("fill"), "#263238")}">{text}</text>'
                )
            elif kind == "polyline":
                points = _mapping_list(payload.get("points"))
                point_text = " ".join(f'{_number(point.get("x"))},{_number(point.get("y"))}' for point in points)
                if len(points) < 2:
                    issues.append(f"svg_renderer_invalid_polyline:{primitive_id}")
                    continue
                stroke_width = max(minimum_line_width_pt, _positive_float(payload.get("stroke_width"), 1.3))
                parts.append(
                    f'<polyline{attrs} points="{point_text}" fill="{_safe_color_or_none(payload.get("fill"), "none")}" '
                    f'stroke="{_safe_color_or_none(payload.get("stroke"), "#455a64")}" stroke-width="{stroke_width:g}" '
                    f'vector-effect="non-scaling-stroke"/>'
                )
                title = escape(str(payload.get("title") or ""))
                if title:
                    parts.append(f'<title>{title}</title>')
            else:
                issues.append(f"svg_renderer_unsupported_primitive:{kind}")
        parts.append("</g>")
        if content:
            parts.append("</g>")
        parts.append("</svg>")
        return "".join(parts)

    def _print_transform(
        self,
        print_layout: Mapping[str, Any],
        render_model: Mapping[str, Any],
        page: Mapping[str, Any] | None = None,
    ) -> tuple[str, float]:
        pages = _mapping_list(print_layout.get("pages"))
        if not bool(print_layout.get("ok")) or not pages:
            return "", 1.0
        selected_page = dict(page or pages[0])
        content = _mapping(selected_page.get("content_bounds"))
        source = _mapping(selected_page.get("source_bounds"))
        dpi = _positive_float(print_layout.get("dpi"), 96.0)
        content_scale = _positive_float(selected_page.get("content_scale"), 1.0)
        source_width = _positive_float(source.get("width"), _positive_float(render_model.get("width"), 1.0))
        source_height = _positive_float(source.get("height"), _positive_float(render_model.get("height"), 1.0))
        if source_width <= 0 or source_height <= 0:
            return "", 1.0
        px_to_pt = 72.0 / dpi
        scale = px_to_pt * content_scale
        tx = (_finite_float(content.get("x")) or 0.0) - (_finite_float(source.get("x")) or 0.0) * scale
        ty = (_finite_float(content.get("y")) or 0.0) - (_finite_float(source.get("y")) or 0.0) * scale
        return f' transform="translate({tx:g} {ty:g}) scale({scale:g})"', scale

    def _extract_scene(self, source: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str, list[str]]:
        source_schema = str(source.get("schema") or "")
        issues: list[str] = []
        if source_schema == "visualization.scene.pipeline.result":
            validation = _mapping(source.get("validation"))
            issues.extend(str(item) for item in _sequence(validation.get("issues")) if str(item))
            return _mapping(source.get("scene")), _mapping(source.get("layout")), source_schema, issues
        if source_schema == "visualization.engine.scene":
            return dict(source), {}, source_schema, issues
        issues.append("svg_renderer_unsupported_source_schema")
        return _mapping(source.get("scene")), _mapping(source.get("layout")), source_schema, issues

    def _render_svg(
        self,
        *,
        tracks: list[dict[str, Any]],
        layer_by_track: dict[str, list[dict[str, Any]]],
        depth_sync: Mapping[str, Any],
        depth_start: float | None,
        depth_stop: float | None,
        track_widths: list[int],
        layout_by_track: dict[str, dict[str, Any]],
        width: int,
        height: int,
        issues: list[str],
    ) -> str:
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="LAS visualization">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            '<g font-family="Arial, DejaVu Sans, sans-serif">',
        ]
        if not tracks:
            parts.extend(
                [
                    '<rect x="12" y="12" width="336" height="120" rx="6" fill="#f5f7fa" stroke="#c7d0d9"/>',
                    '<text x="28" y="52" font-size="15" fill="#263238">Visualization scene is empty</text>',
                    '<text x="28" y="80" font-size="11" fill="#607d8b">No printable tracks or layers were provided.</text>',
                    "</g></svg>",
                ]
            )
            return "".join(parts)

        depth_span = (depth_stop - depth_start) if depth_start is not None and depth_stop is not None else None
        for index, (track, track_width) in enumerate(zip(tracks, track_widths)):
            track_id = str(track.get("id") or f"track.{index}")
            track_layout = _mapping(layout_by_track.get(track_id))
            plot_bounds = _mapping(track_layout.get("plot_bounds"))
            header_bounds = _mapping(track_layout.get("header_bounds"))
            x = int(_positive_float(plot_bounds.get("x"), self.SIDE_PADDING + sum(track_widths[:index])))
            plot_top = int(_positive_float(plot_bounds.get("y"), self.HEADER_HEIGHT + self.AXIS_HEIGHT))
            plot_height = int(_positive_float(plot_bounds.get("height"), self.PLOT_HEIGHT))
            track_width = int(_positive_float(plot_bounds.get("width"), track_width))
            title = escape(str(track.get("title") or track_id))
            style = _mapping(track.get("style"))
            fill = _safe_color(style.get("fill"), "#ffffff")
            parts.append(f'<g data-track="{escape(track_id, quote=True)}">')
            parts.append(f'<rect x="{x}" y="{plot_top}" width="{track_width}" height="{plot_height}" fill="{fill}" stroke="#b0bec5"/>')
            parts.append(f'<text x="{x + 8}" y="{int(_positive_float(header_bounds.get("y"), 0)) + 26}" font-size="12" font-weight="600" fill="#263238">{title}</text>')
            self._append_depth_grid(parts, x=x, width=track_width, plot_top=plot_top, plot_height=plot_height, depth_start=depth_start, depth_stop=depth_stop)
            for layer in layer_by_track.get(track_id, []):
                kind = str(layer.get("kind") or "")
                if kind == "interval_overlay":
                    self._append_overlay(parts, layer, x=x, width=track_width, plot_top=plot_top, plot_height=plot_height, depth_start=depth_start, depth_span=depth_span)
                elif kind == "curve":
                    self._append_curve(parts, layer, x=x, width=track_width, plot_top=plot_top, plot_height=plot_height, depth_start=depth_start, depth_span=depth_span, issues=issues)
            parts.append("</g>")
        unit = escape(str(depth_sync.get("unit") or ""))
        domain_label = "Depth"
        if depth_start is not None and depth_stop is not None:
            domain_label = f"Depth {depth_start:g}–{depth_stop:g} {unit}".strip()
        parts.append(f'<text x="{self.SIDE_PADDING}" y="{height - 7}" font-size="10" fill="#546e7a">{domain_label}</text>')
        parts.append("</g></svg>")
        return "".join(parts)

    def _append_depth_grid(
        self,
        parts: list[str],
        *,
        x: int,
        width: int,
        plot_top: int,
        plot_height: int,
        depth_start: float | None,
        depth_stop: float | None,
    ) -> None:
        for tick in range(6):
            y = plot_top + (plot_height * tick / 5)
            parts.append(f'<line x1="{x}" y1="{y:.2f}" x2="{x + width}" y2="{y:.2f}" stroke="#dfe5ea" stroke-width="0.7"/>')
            if depth_start is not None and depth_stop is not None:
                value = depth_start + (depth_stop - depth_start) * tick / 5
                parts.append(f'<text x="{x + 4}" y="{y + 11:.2f}" font-size="8" fill="#78909c">{value:g}</text>')

    def _append_overlay(
        self,
        parts: list[str],
        layer: Mapping[str, Any],
        *,
        x: int,
        width: int,
        plot_top: int,
        plot_height: int,
        depth_start: float | None,
        depth_span: float | None,
    ) -> None:
        if depth_start is None or not depth_span:
            return
        payload = _mapping(layer.get("payload"))
        top = _finite_float(payload.get("top"))
        base = _finite_float(payload.get("base"))
        if top is None or base is None:
            return
        y1 = plot_top + ((top - depth_start) / depth_span) * plot_height
        y2 = plot_top + ((base - depth_start) / depth_span) * plot_height
        y = max(plot_top, min(y1, y2))
        bottom = min(plot_top + plot_height, max(y1, y2))
        if bottom <= y:
            return
        style = _mapping(payload.get("style"))
        fill = _safe_color(style.get("fill"), "#b0bec5")
        stroke = _safe_color(style.get("stroke"), "#607d8b")
        layer_id = escape(str(layer.get("id") or ""), quote=True)
        label = escape(str(payload.get("label") or ""))
        parts.append(f'<g data-layer="{layer_id}" data-kind="interval_overlay">')
        parts.append(f'<rect x="{x + 1}" y="{y:.2f}" width="{max(width - 2, 1)}" height="{bottom - y:.2f}" fill="{fill}" fill-opacity="0.24" stroke="{stroke}" stroke-opacity="0.55" stroke-width="0.7"/>')
        if label and bottom - y >= 14:
            parts.append(f'<text x="{x + 8}" y="{y + 12:.2f}" font-size="8" fill="#37474f">{label}</text>')
        parts.append("</g>")

    def _append_curve(
        self,
        parts: list[str],
        layer: Mapping[str, Any],
        *,
        x: int,
        width: int,
        plot_top: int,
        plot_height: int,
        depth_start: float | None,
        depth_span: float | None,
        issues: list[str],
    ) -> None:
        if depth_start is None or not depth_span:
            return
        payload = _mapping(layer.get("payload"))
        points = _mapping_list(payload.get("points"))
        if not points:
            issues.append(f'svg_renderer_curve_has_no_points:{layer.get("id", "")}'.rstrip(":"))
            return
        axis = _mapping(payload.get("axis"))
        values = [_finite_float(point.get("value")) for point in points]
        finite_values = [value for value in values if value is not None]
        axis_min = _finite_float(axis.get("min"))
        axis_max = _finite_float(axis.get("max"))
        if axis_min is None and finite_values:
            axis_min = min(finite_values)
        if axis_max is None and finite_values:
            axis_max = max(finite_values)
        if axis_min is None or axis_max is None or axis_max <= axis_min:
            issues.append(f'svg_renderer_invalid_curve_axis:{layer.get("id", "")}'.rstrip(":"))
            return
        scale = str(axis.get("scale") or "linear").lower()
        style = _mapping(payload.get("style"))
        stroke = _safe_color(style.get("stroke"), "#455a64")
        stroke_width = _positive_float(style.get("line_width"), 1.3)
        polyline: list[str] = []
        for point in points:
            depth = _finite_float(point.get("depth"))
            value = _finite_float(point.get("value"))
            if depth is None or value is None:
                continue
            normalized = _normalize_value(value, axis_min, axis_max, scale)
            if normalized is None:
                continue
            px = x + 8 + normalized * max(width - 16, 1)
            py = plot_top + ((depth - depth_start) / depth_span) * plot_height
            if plot_top - 1 <= py <= plot_top + plot_height + 1:
                polyline.append(f"{px:.2f},{py:.2f}")
        if len(polyline) < 2:
            issues.append(f'svg_renderer_curve_has_insufficient_points:{layer.get("id", "")}'.rstrip(":"))
            return
        layer_id = escape(str(layer.get("id") or ""), quote=True)
        mnemonic = escape(str(payload.get("mnemonic") or ""))
        parts.append(f'<g data-layer="{layer_id}" data-kind="curve">')
        parts.append(f'<polyline points="{" ".join(polyline)}" fill="none" stroke="{stroke}" stroke-width="{stroke_width:g}" vector-effect="non-scaling-stroke"/>')
        parts.append(f'<title>{mnemonic}</title>')
        parts.append("</g>")



def _number(value: Any, default: float = 0.0) -> str:
    number = _finite_float(value)
    if number is None:
        number = default
    return f"{number:g}"

def _safe_color_or_none(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if text == "none":
        return "none"
    return _safe_color(text, default)

def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [_mapping(item) for item in _sequence(value) if isinstance(item, Mapping)]


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _string_set(value: Any) -> set[str]:
    return {str(item) for item in _sequence(value) if str(item)}


def _primitive_on_page(primitive: Mapping[str, Any], track_ids: set[str]) -> bool:
    primitive_track_id = str(primitive.get("track_id") or "")
    return not track_ids or not primitive_track_id or primitive_track_id in track_ids


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive_float(value: Any, default: float) -> float:
    number = _finite_float(value)
    return number if number is not None and number > 0 else default


def _safe_color(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if text.startswith("#") and len(text) in {4, 7, 9} and all(char in "0123456789abcdefABCDEF" for char in text[1:]):
        return text
    return default


def _normalize_value(value: float, minimum: float, maximum: float, scale: str) -> float | None:
    if scale == "log":
        if value <= 0 or minimum <= 0 or maximum <= 0:
            return None
        low = math.log10(minimum)
        high = math.log10(maximum)
        if high <= low:
            return None
        return min(1.0, max(0.0, (math.log10(value) - low) / (high - low)))
    return min(1.0, max(0.0, (value - minimum) / (maximum - minimum)))
