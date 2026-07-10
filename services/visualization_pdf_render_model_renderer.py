"""PDF renderer adapter for the renderer-neutral Visualization Render Model.

The adapter consumes only ``VisualizationRenderModel`` and
``VisualizationPrintLayout`` data from a scene pipeline result. It never reads
LAS payloads, scene layers or layout geometry directly. All primitive geometry
is therefore shared with SVG and future renderers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class PdfRenderModelResult:
    """Binary PDF artifact plus machine-readable renderer metadata."""

    schema: str = "visualization.renderer.pdf.result"
    version: str = "1.0"
    renderer: str = "visualization_pdf_render_model_renderer"
    source_schema: str = ""
    primitive_count: int = 0
    clip_count: int = 0
    print_layout_applied: bool = False
    page_size: str = ""
    page_count: int = 0
    width_pt: float = 0.0
    height_pt: float = 0.0
    export_ready: bool = False
    pdf_bytes: bytes = b""
    font_name: str = ""
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "renderer": self.renderer,
            "source_schema": self.source_schema,
            "format": "pdf",
            "primitive_count": self.primitive_count,
            "clip_count": self.clip_count,
            "print_layout_applied": self.print_layout_applied,
            "page_size": self.page_size,
            "page_count": self.page_count,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "export_ready": self.export_ready,
            "byte_size": len(self.pdf_bytes),
            "sha256": sha256(self.pdf_bytes).hexdigest() if self.pdf_bytes else "",
            "font_name": self.font_name,
            "contains_raw_dataframe": False,
            "issues": list(self.issues),
        }


class VisualizationPdfRenderModelRenderer:
    """Render a one-page PDF from pipeline ``render_model`` primitives."""

    def render(self, source: Mapping[str, Any]) -> PdfRenderModelResult:
        source_schema = str(source.get("schema") or "")
        issues: list[str] = []
        if source_schema != "visualization.scene.pipeline.result":
            issues.append("pdf_renderer_unsupported_source_schema")

        render_model = _mapping(source.get("render_model"))
        print_layout = _mapping(source.get("print_layout"))
        if str(render_model.get("schema") or "") != "visualization.render.model":
            issues.append("pdf_renderer_render_model_missing")
        primitives = [item for item in _mapping_list(render_model.get("primitives")) if _enabled(item)]
        clips = _mapping_list(render_model.get("clip_regions"))

        page = _first_mapping(print_layout.get("pages"))
        page_bounds = _mapping(page.get("page_bounds"))
        print_layout_applied = bool(print_layout.get("ok")) and bool(page_bounds)
        if not print_layout_applied:
            issues.append("pdf_renderer_print_layout_missing")
            width_pt = _positive_float(render_model.get("width"), 612.0)
            height_pt = _positive_float(render_model.get("height"), 792.0)
        else:
            width_pt = _positive_float(page_bounds.get("width"), 612.0)
            height_pt = _positive_float(page_bounds.get("height"), 792.0)

        if not primitives:
            issues.append("pdf_renderer_no_printable_primitives")

        try:
            pdf_bytes, font_name, draw_issues = self._draw(
                render_model=render_model,
                print_layout=print_layout,
                width_pt=width_pt,
                height_pt=height_pt,
            )
            issues.extend(draw_issues)
        except ImportError:
            pdf_bytes = b""
            font_name = ""
            issues.append("pdf_renderer_reportlab_unavailable")
        except Exception as exc:  # defensive artifact boundary
            pdf_bytes = b""
            font_name = ""
            issues.append(f"pdf_renderer_error:{type(exc).__name__}")

        export_ready = bool(pdf_bytes.startswith(b"%PDF-") and primitives and not any(i.startswith("pdf_renderer_error:") for i in issues))
        return PdfRenderModelResult(
            source_schema=source_schema,
            primitive_count=len(primitives),
            clip_count=len(clips),
            print_layout_applied=print_layout_applied,
            page_size=str(print_layout.get("page_size") or ""),
            page_count=1 if pdf_bytes else 0,
            width_pt=width_pt,
            height_pt=height_pt,
            export_ready=export_ready,
            pdf_bytes=pdf_bytes,
            font_name=font_name,
            issues=tuple(dict.fromkeys(issues)),
        )

    def _draw(
        self,
        *,
        render_model: Mapping[str, Any],
        print_layout: Mapping[str, Any],
        width_pt: float,
        height_pt: float,
    ) -> tuple[bytes, str, list[str]]:
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=(width_pt, height_pt), pageCompression=1)
        issues: list[str] = []
        font_name = _register_unicode_font(issues)
        clips = {str(item.get("id") or ""): item for item in _mapping_list(render_model.get("clip_regions"))}
        transform = _print_transform(print_layout, render_model)

        for primitive in _mapping_list(render_model.get("primitives")):
            if not _enabled(primitive):
                continue
            pdf.saveState()
            clip_id = str(primitive.get("clip_id") or "")
            if clip_id and clip_id in clips:
                _apply_clip(pdf, clips[clip_id], transform, height_pt)
            _draw_primitive(pdf, primitive, transform, height_pt, font_name, issues)
            pdf.restoreState()

        pdf.showPage()
        pdf.save()
        return buffer.getvalue(), font_name, issues


def _draw_primitive(pdf: Any, primitive: Mapping[str, Any], transform: tuple[float, float, float], page_height: float, font_name: str, issues: list[str]) -> None:
    payload = _mapping(primitive.get("payload"))
    kind = str(primitive.get("kind") or "")
    scale, tx, ty = transform

    if kind == "rectangle":
        x = tx + _float(payload.get("x")) * scale
        y_top = ty + _float(payload.get("y")) * scale
        width = _non_negative_float(payload.get("width")) * scale
        height = _non_negative_float(payload.get("height")) * scale
        y = page_height - y_top - height
        _set_fill(pdf, payload.get("fill"), _float(payload.get("fill_opacity"), 1.0))
        _set_stroke(pdf, payload.get("stroke"), _float(payload.get("stroke_opacity"), 1.0), _positive_float(payload.get("stroke_width"), 1.0) * scale)
        radius = _non_negative_float(payload.get("corner_radius")) * scale
        if radius > 0:
            pdf.roundRect(x, y, width, height, radius, stroke=_has_color(payload.get("stroke")), fill=_has_color(payload.get("fill")))
        else:
            pdf.rect(x, y, width, height, stroke=_has_color(payload.get("stroke")), fill=_has_color(payload.get("fill")))
        return

    if kind == "line":
        x1 = tx + _float(payload.get("x1")) * scale
        y1 = page_height - (ty + _float(payload.get("y1")) * scale)
        x2 = tx + _float(payload.get("x2")) * scale
        y2 = page_height - (ty + _float(payload.get("y2")) * scale)
        _set_stroke(pdf, payload.get("stroke"), 1.0, _positive_float(payload.get("stroke_width"), 1.0) * scale)
        pdf.line(x1, y1, x2, y2)
        return

    if kind == "polyline":
        points = _point_list(payload.get("points"))
        if len(points) < 2:
            return
        _set_stroke(pdf, payload.get("stroke"), 1.0, _positive_float(payload.get("stroke_width"), 1.0) * scale)
        path = pdf.beginPath()
        first_x, first_y = points[0]
        path.moveTo(tx + first_x * scale, page_height - (ty + first_y * scale))
        for x, y in points[1:]:
            path.lineTo(tx + x * scale, page_height - (ty + y * scale))
        pdf.drawPath(path, stroke=1, fill=0)
        return

    if kind == "text":
        text = str(payload.get("text") or "")
        if not text:
            return
        x = tx + _float(payload.get("x")) * scale
        y = page_height - (ty + _float(payload.get("y")) * scale)
        size = max(1.0, _positive_float(payload.get("font_size"), 9.0) * scale)
        _set_fill(pdf, payload.get("fill"), 1.0)
        pdf.setFont(font_name, size)
        anchor = str(payload.get("text_anchor") or "start")
        rotation = _float(payload.get("rotation"), 0.0)
        pdf.saveState()
        pdf.translate(x, y)
        if rotation:
            pdf.rotate(-rotation)
        if anchor == "middle":
            pdf.drawCentredString(0, 0, text)
        elif anchor == "end":
            pdf.drawRightString(0, 0, text)
        else:
            pdf.drawString(0, 0, text)
        pdf.restoreState()
        return

    issues.append(f"pdf_renderer_unsupported_primitive:{kind or 'unknown'}")


def _apply_clip(pdf: Any, clip: Mapping[str, Any], transform: tuple[float, float, float], page_height: float) -> None:
    scale, tx, ty = transform
    x = tx + _float(clip.get("x")) * scale
    y_top = ty + _float(clip.get("y")) * scale
    width = _non_negative_float(clip.get("width")) * scale
    height = _non_negative_float(clip.get("height")) * scale
    path = pdf.beginPath()
    path.rect(x, page_height - y_top - height, width, height)
    pdf.clipPath(path, stroke=0, fill=0)


def _print_transform(print_layout: Mapping[str, Any], render_model: Mapping[str, Any]) -> tuple[float, float, float]:
    page = _first_mapping(print_layout.get("pages"))
    content = _mapping(page.get("content_bounds"))
    source = _mapping(page.get("source_bounds"))
    if bool(print_layout.get("ok")) and content and source:
        source_width = _positive_float(source.get("width"), _positive_float(render_model.get("width"), 1.0))
        scale = _positive_float(content.get("width"), source_width) / source_width
        return scale, _float(content.get("x")), _float(content.get("y"))
    return 1.0, 0.0, 0.0


def _register_unicode_font(issues: list[str]) -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    name = "GasRatioProUnicode"
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    for path in _font_candidates():
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
                return name
            except Exception:
                continue
    issues.append("pdf_renderer_unicode_font_unavailable")
    return "Helvetica"


def _font_candidates() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[1]
    env_path = os.getenv("GAS_RATIO_PRO_PDF_FONT")
    values = [Path(env_path)] if env_path else []
    values.extend([
        root / "assets" / "fonts" / "NotoSans-Regular.ttf",
        root / "assets" / "fonts" / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ])
    return tuple(values)


def _set_fill(pdf: Any, value: Any, opacity: float) -> None:
    color = _parse_color(value)
    if color is None:
        return
    pdf.setFillColorRGB(*color)
    if hasattr(pdf, "setFillAlpha"):
        pdf.setFillAlpha(max(0.0, min(1.0, opacity)))


def _set_stroke(pdf: Any, value: Any, opacity: float, width: float) -> None:
    color = _parse_color(value)
    if color is None:
        return
    pdf.setStrokeColorRGB(*color)
    pdf.setLineWidth(max(0.1, width))
    if hasattr(pdf, "setStrokeAlpha"):
        pdf.setStrokeAlpha(max(0.0, min(1.0, opacity)))


def _parse_color(value: Any) -> tuple[float, float, float] | None:
    text = str(value or "").strip().lower()
    if text in {"", "none", "transparent"}:
        return None
    if text.startswith("#") and len(text) == 7:
        try:
            return tuple(int(text[index:index + 2], 16) / 255.0 for index in (1, 3, 5))  # type: ignore[return-value]
        except ValueError:
            return None
    return {"black": (0.0, 0.0, 0.0), "white": (1.0, 1.0, 1.0)}.get(text, (0.0, 0.0, 0.0))


def _has_color(value: Any) -> int:
    return 1 if _parse_color(value) is not None else 0


def _point_list(value: Any) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return result
    for item in value:
        if isinstance(item, Mapping):
            x = _finite_float(item.get("x"))
            y = _finite_float(item.get("y"))
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)) and len(item) >= 2:
            x = _finite_float(item[0])
            y = _finite_float(item[1])
        else:
            continue
        if x is not None and y is not None:
            result.append((x, y))
    return result


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _first_mapping(value: Any) -> dict[str, Any]:
    values = _mapping_list(value)
    return values[0] if values else {}


def _enabled(item: Mapping[str, Any]) -> bool:
    return bool(item.get("visible", True)) and bool(item.get("printable", True))


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _float(value: Any, default: float = 0.0) -> float:
    parsed = _finite_float(value)
    return parsed if parsed is not None else default


def _positive_float(value: Any, default: float) -> float:
    parsed = _float(value, default)
    return parsed if parsed > 0 else default


def _non_negative_float(value: Any) -> float:
    return max(0.0, _float(value))
