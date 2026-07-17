"""Structural QA for Visualization Engine SVG and PDF exports.

This module belongs to the Visualization Engine QA boundary. It does not draw
primitives and does not contain UI logic. It validates that renderer artifacts
faithfully represent the shared renderer-neutral pipeline contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import math
from typing import Any, Mapping
from xml.etree import ElementTree

from services.visualization_renderer_parity import VisualizationRendererParityValidator
from services.visualization_print_quality import VisualizationPrintQualityValidator


@dataclass(frozen=True, slots=True)
class VisualizationExportQaReport:
    schema: str = "visualization.export.qa.report"
    version: str = "1.0"
    ok: bool = False
    svg_ok: bool = False
    pdf_ok: bool = False
    renderer_parity_ok: bool = False
    geometry_signature_match: bool = False
    print_quality_ok: bool = False
    expected_primitive_count: int = 0
    svg_primitive_count: int = 0
    expected_clip_count: int = 0
    svg_clip_count: int = 0
    pdf_page_count: int = 0
    page_width_pt: float = 0.0
    page_height_pt: float = 0.0
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "ok": self.ok,
            "svg_ok": self.svg_ok,
            "pdf_ok": self.pdf_ok,
            "renderer_parity_ok": self.renderer_parity_ok,
            "geometry_signature_match": self.geometry_signature_match,
            "print_quality_ok": self.print_quality_ok,
            "expected_primitive_count": self.expected_primitive_count,
            "svg_primitive_count": self.svg_primitive_count,
            "expected_clip_count": self.expected_clip_count,
            "svg_clip_count": self.svg_clip_count,
            "pdf_page_count": self.pdf_page_count,
            "page_width_pt": self.page_width_pt,
            "page_height_pt": self.page_height_pt,
            "issues": list(self.issues),
            "renderer_neutral": True,
        }


class VisualizationExportQaValidator:
    """Validate SVG/PDF exports against one scene pipeline result."""

    _SVG_NS = "{http://www.w3.org/2000/svg}"

    def validate(self, pipeline: Mapping[str, Any], svg_result: Any, pdf_result: Any) -> VisualizationExportQaReport:
        svg_meta, svg_text = _renderer_payload(svg_result, text_field="svg")
        pdf_meta, pdf_bytes = _renderer_payload(pdf_result, bytes_field="pdf_bytes")
        render_model = _mapping(pipeline.get("render_model"))
        expected_primitives = [
            item for item in _mapping_list(render_model.get("primitives"))
            if bool(item.get("visible", True)) and bool(item.get("printable", True))
        ]
        print_layout = _mapping(pipeline.get("print_layout"))
        expected_page_primitives = [
            primitive
            for page in _mapping_list(print_layout.get("pages"))
            for primitive in _mapping_list(page.get("chrome_primitives"))
            if bool(primitive.get("visible", True)) and bool(primitive.get("printable", True))
        ]
        expected_primitive_ids = {
            str(item.get("id") or "")
            for item in [*expected_primitives, *expected_page_primitives]
            if str(item.get("id") or "")
        }
        expected_clips = _mapping_list(render_model.get("clip_regions"))
        issues: list[str] = []

        print_quality = VisualizationPrintQualityValidator().validate(pipeline)
        if not print_quality.ok:
            issues.extend(f"export_qa_print_quality:{item}" for item in print_quality.issues)

        svg_parity = VisualizationRendererParityValidator().validate(pipeline, svg_meta)
        pdf_parity = VisualizationRendererParityValidator().validate(pipeline, pdf_meta)
        renderer_parity_ok = svg_parity.ok and pdf_parity.ok
        if not svg_parity.ok:
            issues.extend(f"export_qa_svg_parity:{item}" for item in svg_parity.issues)
        if not pdf_parity.ok:
            issues.extend(f"export_qa_pdf_parity:{item}" for item in pdf_parity.issues)

        svg_pages = [svg_text]
        declared_svg_pages = svg_meta.get("page_svgs")
        if isinstance(declared_svg_pages, (list, tuple)):
            svg_pages.extend(str(item) for item in declared_svg_pages[1:])
        svg_ok, svg_primitive_count, svg_clip_count, svg_issues = self._validate_svg(
            svg_pages,
            svg_meta,
            expected_primitive_ids=expected_primitive_ids,
            expected_clip_ids={str(item.get("id") or "") for item in expected_clips},
        )
        issues.extend(svg_issues)

        pdf_ok, pdf_page_count, page_width, page_height, pdf_issues = self._validate_pdf(pdf_bytes, pdf_meta)
        issues.extend(pdf_issues)

        svg_signature = str(svg_meta.get("geometry_signature") or "")
        pdf_signature = str(pdf_meta.get("geometry_signature") or "")
        geometry_signature_match = bool(svg_signature and svg_signature == pdf_signature)
        if not geometry_signature_match:
            issues.append("export_qa_renderer_geometry_signature_mismatch")

        return VisualizationExportQaReport(
            ok=svg_ok and pdf_ok and renderer_parity_ok and geometry_signature_match and print_quality.ok and not issues,
            svg_ok=svg_ok,
            pdf_ok=pdf_ok,
            renderer_parity_ok=renderer_parity_ok,
            geometry_signature_match=geometry_signature_match,
            print_quality_ok=print_quality.ok,
            expected_primitive_count=len(expected_primitive_ids),
            svg_primitive_count=svg_primitive_count,
            expected_clip_count=len(expected_clips),
            svg_clip_count=svg_clip_count,
            pdf_page_count=pdf_page_count,
            page_width_pt=page_width,
            page_height_pt=page_height,
            issues=tuple(dict.fromkeys(issues)),
        )

    def _validate_svg(
        self,
        svg_pages: list[str],
        metadata: Mapping[str, Any],
        *,
        expected_primitive_ids: set[str],
        expected_clip_ids: set[str],
    ) -> tuple[bool, int, int, list[str]]:
        issues: list[str] = []
        if not svg_pages or not svg_pages[0].strip():
            return False, 0, 0, ["export_qa_svg_missing"]
        roots: list[Any] = []
        for page_index, svg in enumerate(svg_pages, start=1):
            if not svg.strip():
                issues.append(f"export_qa_svg_page_missing:{page_index}")
                continue
            try:
                root = ElementTree.fromstring(svg)
            except ElementTree.ParseError:
                issues.append("export_qa_svg_invalid_xml" if page_index == 1 else f"export_qa_svg_page_invalid_xml:{page_index}")
                continue
            roots.append(root)
            if root.tag != f"{self._SVG_NS}svg":
                issues.append(f"export_qa_svg_root_invalid:{page_index}")
            page_primitive_ids = [
                node.attrib.get("data-primitive", "")
                for node in root.iter()
                if "data-primitive" in node.attrib
            ]
            if len(set(page_primitive_ids)) != len(page_primitive_ids):
                issues.append(f"export_qa_svg_duplicate_primitive_ids:{page_index}")

        primitive_ids = {
            node.attrib.get("data-primitive", "")
            for root in roots
            for node in root.iter()
            if "data-primitive" in node.attrib
        }
        clip_ids = {
            node.attrib.get("id", "")
            for root in roots
            for node in root.iter(f"{self._SVG_NS}clipPath")
            if node.attrib.get("id") != "print-page-content"
        }
        if primitive_ids != expected_primitive_ids:
            issues.append(
                f"export_qa_svg_primitive_count_mismatch:{len(expected_primitive_ids)}:{len(primitive_ids)}"
            )
        if clip_ids != expected_clip_ids:
            issues.append(f"export_qa_svg_clip_count_mismatch:{len(expected_clip_ids)}:{len(clip_ids)}")

        expected_pages = int(metadata.get("page_count") or 0)
        if len(svg_pages) != expected_pages:
            issues.append(f"export_qa_svg_page_count_mismatch:{expected_pages}:{len(svg_pages)}")
        root = roots[0] if roots else None
        width = _positive_float(root.attrib.get("width")) if root is not None else 0.0
        height = _positive_float(root.attrib.get("height")) if root is not None else 0.0
        if not _close(width, _positive_float(metadata.get("width"))):
            issues.append("export_qa_svg_width_mismatch")
        if not _close(height, _positive_float(metadata.get("height"))):
            issues.append("export_qa_svg_height_mismatch")
        if not bool(metadata.get("export_ready")):
            issues.append("export_qa_svg_not_export_ready")
        return not issues, len(primitive_ids), len(clip_ids), issues

    def _validate_pdf(
        self,
        pdf_bytes: bytes,
        metadata: Mapping[str, Any],
    ) -> tuple[bool, int, float, float, list[str]]:
        issues: list[str] = []
        if not pdf_bytes.startswith(b"%PDF-"):
            return False, 0, 0.0, 0.0, ["export_qa_pdf_missing_or_invalid_header"]
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(pdf_bytes), strict=True)
            page_count = len(reader.pages)
            if page_count:
                box = reader.pages[0].mediabox
                width = float(box.width)
                height = float(box.height)
            else:
                width = height = 0.0
        except Exception as exc:
            return False, 0, 0.0, 0.0, [f"export_qa_pdf_parse_error:{type(exc).__name__}"]

        expected_pages = int(metadata.get("page_count") or 0)
        if page_count != expected_pages:
            issues.append(f"export_qa_pdf_page_count_mismatch:{expected_pages}:{page_count}")
        if not _close(width, _positive_float(metadata.get("width_pt")), tolerance=0.05):
            issues.append("export_qa_pdf_width_mismatch")
        if not _close(height, _positive_float(metadata.get("height_pt")), tolerance=0.05):
            issues.append("export_qa_pdf_height_mismatch")
        if not str(metadata.get("font_name") or ""):
            issues.append("export_qa_pdf_unicode_font_missing")
        if not bool(metadata.get("export_ready")):
            issues.append("export_qa_pdf_not_export_ready")
        return not issues, page_count, width, height, issues


def _renderer_payload(value: Any, *, text_field: str = "", bytes_field: str = "") -> tuple[dict[str, Any], Any]:
    metadata = value.to_dict() if hasattr(value, "to_dict") else _mapping(value)
    payload: Any = "" if text_field else b""
    if text_field:
        payload = getattr(value, text_field, None)
        if payload is None:
            payload = metadata.get(text_field, "")
    elif bytes_field:
        payload = getattr(value, bytes_field, None)
        if payload is None:
            payload = metadata.get(bytes_field, b"")
    return metadata, payload if isinstance(payload, (str, bytes)) else ("" if text_field else b"")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _positive_float(value: Any) -> float:
    try:
        text = str(value or "").strip().lower()
        if text.endswith("pt"):
            text = text[:-2]
        number = float(text)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) and number > 0 else 0.0


def _close(left: float, right: float, *, tolerance: float = 1e-6) -> bool:
    return left > 0 and right > 0 and abs(left - right) <= tolerance
