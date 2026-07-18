"""Delivery adapter for page-aware SVG/PNG/PDF artifacts.

Multi-page SVG and PNG output is always delivered as a ZIP bundle.  Returning
page one as if it represented the complete physical document is forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
import re
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from services.visualization_page_aware_package import VisualizationPageAwarePackage


@dataclass(frozen=True, slots=True)
class PageAwareStaticArtifact:
    content: bytes
    file_name: str
    mime_type: str
    format: str
    page_count: int
    bundled: bool

    @property
    def ok(self) -> bool:
        return bool(self.content) and self.page_count > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.page-aware.static-artifact",
            "version": "1.0",
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "format": self.format,
            "page_count": self.page_count,
            "bundled": self.bundled,
            "byte_size": len(self.content),
            "ok": self.ok,
            "single_page_fallback": False,
        }


def build_page_aware_static_artifact(
    package: VisualizationPageAwarePackage,
    *,
    format_name: str,
    base_name: str,
) -> PageAwareStaticArtifact:
    if not package.export_ready:
        raise ValueError("page_aware_static_export_package_not_ready")
    normalized = str(format_name or "").strip().lower()
    safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", str(base_name or "visualization")).strip("._") or "visualization"
    if normalized == "pdf":
        return PageAwareStaticArtifact(
            content=package.pdf_bytes,
            file_name=f"{safe_base}.pdf",
            mime_type="application/pdf",
            format="pdf",
            page_count=package.page_count,
            bundled=False,
        )
    if normalized not in {"svg", "png"}:
        raise ValueError(f"page_aware_static_export_unsupported_format:{normalized}")

    payloads: tuple[bytes, ...]
    mime_type: str
    if normalized == "svg":
        payloads = tuple(page.svg.encode("utf-8") for page in package.pages)
        mime_type = "image/svg+xml"
    else:
        payloads = tuple(page.png_bytes for page in package.pages)
        mime_type = "image/png"

    if package.page_count == 1:
        return PageAwareStaticArtifact(
            content=payloads[0],
            file_name=f"{safe_base}.{normalized}",
            mime_type=mime_type,
            format=normalized,
            page_count=1,
            bundled=False,
        )

    manifest = {
        "schema": "visualization.page-aware.static-bundle",
        "version": "1.0",
        "format": normalized,
        "page_count": package.page_count,
        "profile_id": package.profile_id,
        "page_size": package.page_size,
        "orientation": package.orientation,
        "geometry_signature": package.geometry_signature,
        "parity_gate_id": str(package.parity_gate.get("gate_id") or ""),
        "cross_format_parity_passed": bool(package.parity_gate.get("ok")),
        "files": [f"{safe_base}_page_{index:03d}.{normalized}" for index in range(1, package.page_count + 1)],
        "single_page_fallback": False,
    }
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for index, payload in enumerate(payloads, start=1):
            archive.writestr(f"{safe_base}_page_{index:03d}.{normalized}", payload)
    return PageAwareStaticArtifact(
        content=buffer.getvalue(),
        file_name=f"{safe_base}_{normalized}_pages.zip",
        mime_type="application/zip",
        format=normalized,
        page_count=package.page_count,
        bundled=True,
    )


__all__ = ["PageAwareStaticArtifact", "build_page_aware_static_artifact"]
