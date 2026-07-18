"""Automated cross-format parity gate for physical visualization exports.

The gate is deliberately independent from UI and delivery adapters.  It blocks
an export package unless SVG, PNG, PDF and the direct DOCX/HTML preview contract
all describe the same physical pages, track partition and geometry signature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
import json
import re
import struct
from typing import Any, Mapping, Sequence

from services.visualization_renderer_parity import visualization_geometry_signature


@dataclass(frozen=True, slots=True)
class VisualizationCrossFormatParityResult:
    schema: str = "visualization.cross-format-parity.result"
    version: str = "1.0"
    gate_id: str = ""
    expected_page_count: int = 0
    format_page_counts: Mapping[str, int] = field(default_factory=dict)
    geometry_signature: str = ""
    geometry_signature_match: bool = False
    physical_page_match: bool = False
    track_partition_match: bool = False
    preview_contract_match: bool = False
    legacy_static_export_detected: bool = False
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return (
            self.expected_page_count > 0
            and self.geometry_signature_match
            and self.physical_page_match
            and self.track_partition_match
            and self.preview_contract_match
            and not self.legacy_static_export_detected
            and not self.issues
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "gate_id": self.gate_id,
            "expected_page_count": self.expected_page_count,
            "format_page_counts": dict(self.format_page_counts),
            "geometry_signature": self.geometry_signature,
            "geometry_signature_match": self.geometry_signature_match,
            "physical_page_match": self.physical_page_match,
            "track_partition_match": self.track_partition_match,
            "preview_contract_match": self.preview_contract_match,
            "legacy_static_export_detected": self.legacy_static_export_detected,
            "issues": list(self.issues),
            "ok": self.ok,
            "blocking": True,
            "formats": ["svg", "png", "pdf", "docx", "html"],
            "single_pipeline_source": True,
        }


class VisualizationCrossFormatParityGate:
    """Validate all physical output adapters before release or user delivery."""

    def validate(
        self,
        pipeline: Mapping[str, Any],
        *,
        svg_result: Any,
        pdf_result: Any,
        png_result: Any,
        package_pages: Sequence[Any],
        preview_contract: Mapping[str, Any],
        raster_dpi: int,
    ) -> VisualizationCrossFormatParityResult:
        issues: list[str] = []
        print_layout = _mapping(pipeline.get("print_layout"))
        layout_pages = _mapping_list(print_layout.get("pages"))
        expected_page_count = len(layout_pages)
        if str(pipeline.get("schema") or "") != "visualization.scene.pipeline.result":
            issues.append("cross_format_parity_unsupported_pipeline_schema")
        if expected_page_count < 1:
            issues.append("cross_format_parity_print_pages_missing")

        svg_count = int(getattr(svg_result, "page_count", 0) or 0)
        png_count = int(getattr(png_result, "page_count", 0) or 0)
        pdf_declared_count = int(getattr(pdf_result, "page_count", 0) or 0)
        pdf_actual_count = _pdf_page_count(getattr(pdf_result, "pdf_bytes", b""))
        preview_pages = _mapping_list(preview_contract.get("pages"))
        preview_count = len(preview_pages)
        package_count = len(package_pages)
        format_page_counts = {
            "layout": expected_page_count,
            "package": package_count,
            "svg": svg_count,
            "png": png_count,
            "pdf": pdf_actual_count,
            "pdf_declared": pdf_declared_count,
            "docx_preview": preview_count,
            "html_preview": preview_count,
        }
        for format_name, count in format_page_counts.items():
            if count != expected_page_count:
                issues.append(
                    f"cross_format_parity_page_count_mismatch:{format_name}:{expected_page_count}:{count}"
                )

        expected_signature = visualization_geometry_signature(pipeline)
        signatures = {
            "expected": expected_signature,
            "svg": str(getattr(svg_result, "geometry_signature", "") or ""),
            "png": str(getattr(png_result, "geometry_signature", "") or ""),
            "pdf": str(getattr(pdf_result, "geometry_signature", "") or ""),
            "preview": str(preview_contract.get("geometry_signature") or ""),
        }
        geometry_signature_match = bool(expected_signature) and all(
            value == expected_signature for value in signatures.values()
        )
        if not geometry_signature_match:
            issues.append("cross_format_parity_geometry_signature_mismatch")

        physical_page_match = self._validate_physical_pages(
            layout_pages=layout_pages,
            svg_pages=tuple(getattr(svg_result, "page_svgs", ()) or ()),
            png_pages=tuple(getattr(png_result, "page_pngs", ()) or ()),
            package_pages=package_pages,
            preview_pages=preview_pages,
            raster_dpi=max(72, min(int(raster_dpi or 300), 600)),
            issues=issues,
        )
        expected_tracks = [tuple(str(item) for item in page.get("track_ids", ()) if str(item)) for page in layout_pages]
        package_tracks = [tuple(str(item) for item in getattr(page, "track_ids", ()) if str(item)) for page in package_pages]
        preview_tracks = [tuple(str(item) for item in page.get("track_ids", ()) if str(item)) for page in preview_pages]
        track_partition_match = expected_tracks == package_tracks == preview_tracks
        if not track_partition_match:
            issues.append("cross_format_parity_track_partition_mismatch")

        preview_contract_match = (
            str(preview_contract.get("schema") or "") == "visualization.preview.page-aware"
            and bool(preview_contract.get("direct_multi_page"))
            and preview_contract.get("single_page_fallback") is False
            and preview_contract.get("legacy_svg_fallback_allowed") is False
            and preview_count == expected_page_count
        )
        if not preview_contract_match:
            issues.append("cross_format_parity_preview_contract_mismatch")

        legacy_static_export_detected = bool(
            preview_contract.get("single_page_fallback")
            or preview_contract.get("legacy_svg_fallback_allowed")
            or str(preview_contract.get("kind") or "") != "page_aware_svg_preview"
        )
        if legacy_static_export_detected:
            issues.append("cross_format_parity_legacy_static_export_detected")

        canonical = {
            "signature": expected_signature,
            "counts": format_page_counts,
            "dimensions": [
                [_number(_mapping(page.get("page_bounds")).get("width")), _number(_mapping(page.get("page_bounds")).get("height"))]
                for page in layout_pages
            ],
            "tracks": [list(items) for items in expected_tracks],
            "profile_id": str(print_layout.get("profile_id") or ""),
            "raster_dpi": max(72, min(int(raster_dpi or 300), 600)),
        }
        gate_id = sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return VisualizationCrossFormatParityResult(
            gate_id=gate_id,
            expected_page_count=expected_page_count,
            format_page_counts=format_page_counts,
            geometry_signature=expected_signature,
            geometry_signature_match=geometry_signature_match,
            physical_page_match=physical_page_match,
            track_partition_match=track_partition_match,
            preview_contract_match=preview_contract_match,
            legacy_static_export_detected=legacy_static_export_detected,
            issues=tuple(dict.fromkeys(issues)),
        )

    @staticmethod
    def _validate_physical_pages(
        *,
        layout_pages: Sequence[Mapping[str, Any]],
        svg_pages: Sequence[str],
        png_pages: Sequence[bytes],
        package_pages: Sequence[Any],
        preview_pages: Sequence[Mapping[str, Any]],
        raster_dpi: int,
        issues: list[str],
    ) -> bool:
        matches = True
        for offset, layout_page in enumerate(layout_pages):
            bounds = _mapping(layout_page.get("page_bounds"))
            expected_width = _number(bounds.get("width"))
            expected_height = _number(bounds.get("height"))
            if expected_width <= 0 or expected_height <= 0:
                issues.append(f"cross_format_parity_invalid_page_bounds:{offset + 1}")
                matches = False
                continue

            if offset >= len(package_pages) or offset >= len(preview_pages):
                matches = False
                continue
            package_page = package_pages[offset]
            preview_page = preview_pages[offset]
            if not _close(float(getattr(package_page, "width_pt", 0.0)), expected_width) or not _close(
                float(getattr(package_page, "height_pt", 0.0)), expected_height
            ):
                issues.append(f"cross_format_parity_package_page_size_mismatch:{offset + 1}")
                matches = False
            if not _close(_number(preview_page.get("width_pt")), expected_width) or not _close(
                _number(preview_page.get("height_pt")), expected_height
            ):
                issues.append(f"cross_format_parity_preview_page_size_mismatch:{offset + 1}")
                matches = False

            if offset < len(svg_pages):
                svg_width, svg_height = _svg_size(svg_pages[offset])
                if not _close(svg_width, expected_width) or not _close(svg_height, expected_height):
                    issues.append(f"cross_format_parity_svg_page_size_mismatch:{offset + 1}")
                    matches = False
                preview_svg = str(preview_page.get("svg") or "")
                if sha256(preview_svg.encode("utf-8")).digest() != sha256(svg_pages[offset].encode("utf-8")).digest():
                    issues.append(f"cross_format_parity_preview_svg_mismatch:{offset + 1}")
                    matches = False
            else:
                matches = False

            if offset < len(png_pages):
                png_width, png_height = _png_size(png_pages[offset])
                expected_png_width = round(expected_width * raster_dpi / 72.0)
                expected_png_height = round(expected_height * raster_dpi / 72.0)
                if abs(png_width - expected_png_width) > 2 or abs(png_height - expected_png_height) > 2:
                    issues.append(f"cross_format_parity_png_page_size_mismatch:{offset + 1}")
                    matches = False
            else:
                matches = False
        return matches


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _close(left: float, right: float, tolerance: float = 0.51) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def _svg_size(svg: str) -> tuple[float, float]:
    root = str(svg or "")[:1000]
    width_match = re.search(r'\bwidth="([0-9.]+)(?:pt)?"', root)
    height_match = re.search(r'\bheight="([0-9.]+)(?:pt)?"', root)
    if width_match and height_match:
        return float(width_match.group(1)), float(height_match.group(1))
    view_box = re.search(r'\bviewBox="[0-9.+-]+\s+[0-9.+-]+\s+([0-9.]+)\s+([0-9.]+)"', root)
    return (float(view_box.group(1)), float(view_box.group(2))) if view_box else (0.0, 0.0)


def _png_size(payload: bytes) -> tuple[int, int]:
    if not isinstance(payload, (bytes, bytearray)) or not payload.startswith(b"\x89PNG\r\n\x1a\n") or len(payload) < 24:
        return 0, 0
    return struct.unpack(">II", payload[16:24])


def _pdf_page_count(payload: bytes) -> int:
    if not isinstance(payload, (bytes, bytearray)) or not payload.startswith(b"%PDF-"):
        return 0
    try:
        from pypdf import PdfReader

        return len(PdfReader(BytesIO(bytes(payload))).pages)
    except Exception:
        return 0


__all__ = ["VisualizationCrossFormatParityGate", "VisualizationCrossFormatParityResult"]
