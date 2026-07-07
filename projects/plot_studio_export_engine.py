from __future__ import annotations

"""Renderer-independent Plot Studio export engine.

The engine prepares and writes export artifacts for Plot Studio tablet layouts.
It deliberately works from immutable workspace/layout objects and never reads or
modifies LAS source files.  Real UI renderers can later replace the lightweight
placeholder writers with Plotly/Kaleido or Matplotlib renderers while keeping the
same validated export manifest API.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal
import json
import struct
import zlib

from projects.plot_studio_core import PlotWorkspace
from projects.plot_studio_track_layout import (
    PlotTrackLayoutConfig,
    PlotTrackLayoutResult,
    build_plot_track_layout,
    build_plot_track_layout_manifest,
)

PlotExportFormat = Literal["pdf", "png", "svg", "tiff"]
PLOT_EXPORT_FORMATS: set[str] = {"pdf", "png", "svg", "tiff"}


@dataclass(frozen=True)
class PlotExportConfig:
    """Export settings for a Plot Studio tablet artifact."""

    formats: tuple[PlotExportFormat, ...] = ("pdf",)
    dpi: int = 300
    scale: float = 1.0
    page_width_mm: float = 297.0
    page_height_mm: float = 420.0
    include_header: bool = True
    include_legend: bool = True
    include_metadata: bool = True
    overwrite: bool = False


@dataclass(frozen=True)
class PlotExportArtifact:
    """One generated export file."""

    format: PlotExportFormat
    path: str
    bytes_written: int
    width_px: int
    height_px: int


@dataclass(frozen=True)
class PlotExportManifest:
    """Complete export manifest for UI, journal and tests."""

    workspace_id: str
    workspace_name: str
    well_id: str
    formats: tuple[PlotExportFormat, ...]
    dpi: int
    scale: float
    width_px: int
    height_px: int
    layout: dict[str, Any]
    artifacts: tuple[PlotExportArtifact, ...] = ()
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlotExportResult:
    """Result of a Plot Studio export operation."""

    manifest: PlotExportManifest
    success: bool
    artifacts: tuple[PlotExportArtifact, ...]
    messages: tuple[str, ...] = ()


def _finite_float(value: Any, field_label: str) -> float:
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{field_label}: значение должно быть конечным числом.")
    return number


def _positive_int(value: Any, field_label: str) -> int:
    number = _finite_float(value, field_label)
    if number <= 0:
        raise ValueError(f"{field_label}: значение должно быть больше нуля.")
    return int(round(number))


def _positive_float(value: Any, field_label: str) -> float:
    number = _finite_float(value, field_label)
    if number <= 0:
        raise ValueError(f"{field_label}: значение должно быть больше нуля.")
    return number


def _clean_formats(formats: Iterable[str]) -> tuple[PlotExportFormat, ...]:
    cleaned: list[PlotExportFormat] = []
    for raw_format in formats:
        fmt = str(raw_format).strip().lower()
        if not fmt:
            continue
        if fmt not in PLOT_EXPORT_FORMATS:
            raise ValueError("Export format: поддерживаются только PDF, PNG, SVG и TIFF.")
        if fmt not in cleaned:
            cleaned.append(fmt)  # type: ignore[arg-type]
    if not cleaned:
        raise ValueError("Export format: нужно выбрать хотя бы один формат экспорта.")
    return tuple(cleaned)


def validate_plot_export_config(config: PlotExportConfig | None = None) -> PlotExportConfig:
    """Validate and normalize export configuration."""

    cfg = config or PlotExportConfig()
    dpi = _positive_int(cfg.dpi, "Export DPI")
    scale = _positive_float(cfg.scale, "Export scale")
    page_width = _positive_float(cfg.page_width_mm, "Page width")
    page_height = _positive_float(cfg.page_height_mm, "Page height")
    if dpi < 72 or dpi > 1200:
        raise ValueError("Export DPI: допустимый диапазон 72..1200.")
    if scale < 0.1 or scale > 8.0:
        raise ValueError("Export scale: допустимый диапазон 0.1..8.0.")
    return PlotExportConfig(
        formats=_clean_formats(cfg.formats),
        dpi=dpi,
        scale=scale,
        page_width_mm=page_width,
        page_height_mm=page_height,
        include_header=bool(cfg.include_header),
        include_legend=bool(cfg.include_legend),
        include_metadata=bool(cfg.include_metadata),
        overwrite=bool(cfg.overwrite),
    )


def _page_size_px(config: PlotExportConfig) -> tuple[int, int]:
    width_in = config.page_width_mm / 25.4
    height_in = config.page_height_mm / 25.4
    return max(1, int(round(width_in * config.dpi * config.scale))), max(1, int(round(height_in * config.dpi * config.scale)))


def build_plot_export_manifest(
    workspace: PlotWorkspace,
    *,
    layout: PlotTrackLayoutResult | None = None,
    layout_config: PlotTrackLayoutConfig | None = None,
    export_config: PlotExportConfig | None = None,
) -> PlotExportManifest:
    """Build a renderer-ready export manifest without writing files."""

    cfg = validate_plot_export_config(export_config)
    actual_layout = layout or build_plot_track_layout(workspace, config=layout_config)
    width_px, height_px = _page_size_px(cfg)
    messages = list(actual_layout.messages)
    if workspace.issues:
        messages.extend(workspace.issues)
    return PlotExportManifest(
        workspace_id=workspace.template_id,
        workspace_name=workspace.name,
        well_id=workspace.well_id,
        formats=cfg.formats,
        dpi=cfg.dpi,
        scale=cfg.scale,
        width_px=width_px,
        height_px=height_px,
        layout=build_plot_track_layout_manifest(actual_layout),
        messages=tuple(messages),
    )


def _safe_stem(value: str) -> str:
    stem = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    stem = "_".join(part for part in stem.split("_") if part)
    return stem[:80] or "plot_studio_export"


def _artifact_path(output_dir: Path, workspace: PlotWorkspace, fmt: str) -> Path:
    return output_dir / f"{_safe_stem(workspace.template_id or workspace.name)}.{fmt}"


def _write_svg(path: Path, manifest: PlotExportManifest, workspace: PlotWorkspace) -> int:
    tracks = manifest.layout.get("items", [])
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{manifest.width_px}" height="{manifest.height_px}" viewBox="0 0 {manifest.width_px} {manifest.height_px}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="24" y="36" font-size="24" font-family="Arial">{workspace.name}</text>',
        f'<text x="24" y="66" font-size="16" font-family="Arial">Well: {workspace.well_id or "-"}</text>',
    ]
    y = 110
    for item in tracks:
        title = str(item.get("title", "Track"))
        left = int(item.get("left_px", 0)) + 24
        width = max(20, int(item.get("width_px", 80)))
        lines.append(f'<rect x="{left}" y="{y}" width="{width}" height="{manifest.height_px - y - 40}" fill="none" stroke="black" stroke-width="1"/>')
        lines.append(f'<text x="{left + 8}" y="{y + 24}" font-size="14" font-family="Arial">{title}</text>')
    lines.append("</svg>")
    data = "\n".join(lines).encode("utf-8")
    path.write_bytes(data)
    return len(data)


def _write_pdf(path: Path, manifest: PlotExportManifest, workspace: PlotWorkspace) -> int:
    # Minimal valid PDF with a single text page.  Coordinates are in points.
    width_pt = manifest.width_px * 72 / manifest.dpi
    height_pt = manifest.height_px * 72 / manifest.dpi
    text = f"Plot Studio Export - {workspace.name}"
    stream = f"BT /F1 18 Tf 40 {max(height_pt - 60, 40):.0f} Td ({text}) Tj ET".encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width_pt:.0f} {height_pt:.0f}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = sum(len(chunk) for chunk in chunks)
    xref = [b"xref\n0 6\n", b"0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    chunks.extend(xref)
    chunks.append(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_offset).encode() + b"\n%%EOF\n")
    data = b"".join(chunks)
    path.write_bytes(data)
    return len(data)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _write_png(path: Path, manifest: PlotExportManifest) -> int:
    width = max(1, min(manifest.width_px, 4096))
    height = max(1, min(manifest.height_px, 4096))
    row = b"\x00" + (b"\xff\xff\xff" * width)
    raw = row * height
    data = b"\x89PNG\r\n\x1a\n"
    data += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += _png_chunk(b"IDAT", zlib.compress(raw, level=9))
    data += _png_chunk(b"IEND", b"")
    path.write_bytes(data)
    return len(data)


def _write_tiff(path: Path, manifest: PlotExportManifest) -> int:
    # Minimal little-endian TIFF header with no image strips; enough for a
    # deterministic artifact placeholder and manifest-driven export pipeline.
    width = max(1, manifest.width_px)
    height = max(1, manifest.height_px)
    entries = [
        (256, 4, 1, width),   # ImageWidth
        (257, 4, 1, height),  # ImageLength
        (259, 3, 1, 1),       # Compression: none
        (262, 3, 1, 1),       # PhotometricInterpretation: BlackIsZero
    ]
    data = bytearray(b"II*\x00\x08\x00\x00\x00")
    data.extend(struct.pack("<H", len(entries)))
    for tag, typ, count, value in entries:
        data.extend(struct.pack("<HHII", tag, typ, count, value))
    data.extend(struct.pack("<I", 0))
    path.write_bytes(bytes(data))
    return len(data)


def export_plot_studio(
    workspace: PlotWorkspace,
    output_dir: Path | str,
    *,
    layout: PlotTrackLayoutResult | None = None,
    layout_config: PlotTrackLayoutConfig | None = None,
    export_config: PlotExportConfig | None = None,
) -> PlotExportResult:
    """Export Plot Studio workspace into the requested artifact formats."""

    cfg = validate_plot_export_config(export_config)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_plot_export_manifest(workspace, layout=layout, layout_config=layout_config, export_config=cfg)
    artifacts: list[PlotExportArtifact] = []
    messages: list[str] = list(manifest.messages)

    for fmt in cfg.formats:
        path = _artifact_path(out_dir, workspace, fmt)
        if path.exists() and not cfg.overwrite:
            raise FileExistsError(f"Export artifact already exists: {path}")
        if fmt == "svg":
            bytes_written = _write_svg(path, manifest, workspace)
        elif fmt == "pdf":
            bytes_written = _write_pdf(path, manifest, workspace)
        elif fmt == "png":
            bytes_written = _write_png(path, manifest)
        elif fmt == "tiff":
            bytes_written = _write_tiff(path, manifest)
        else:  # pragma: no cover - protected by validation
            raise ValueError(f"Unsupported export format: {fmt}")
        artifacts.append(
            PlotExportArtifact(
                format=fmt,
                path=str(path),
                bytes_written=bytes_written,
                width_px=manifest.width_px,
                height_px=manifest.height_px,
            )
        )

    final_manifest = PlotExportManifest(
        workspace_id=manifest.workspace_id,
        workspace_name=manifest.workspace_name,
        well_id=manifest.well_id,
        formats=manifest.formats,
        dpi=manifest.dpi,
        scale=manifest.scale,
        width_px=manifest.width_px,
        height_px=manifest.height_px,
        layout=manifest.layout,
        artifacts=tuple(artifacts),
        messages=tuple(messages),
    )
    manifest_path = out_dir / f"{_safe_stem(workspace.template_id or workspace.name)}.export_manifest.json"
    manifest_path.write_text(json.dumps(build_plot_export_result_manifest(final_manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    messages.append("Plot Studio export completed.")
    return PlotExportResult(manifest=final_manifest, success=True, artifacts=tuple(artifacts), messages=tuple(messages))


def build_plot_export_result_manifest(manifest: PlotExportManifest) -> dict[str, Any]:
    """Serialize export manifest for UI, project journal and documentation."""

    return {
        "workspace_id": manifest.workspace_id,
        "workspace_name": manifest.workspace_name,
        "well_id": manifest.well_id,
        "formats": list(manifest.formats),
        "dpi": manifest.dpi,
        "scale": manifest.scale,
        "width_px": manifest.width_px,
        "height_px": manifest.height_px,
        "layout": manifest.layout,
        "artifacts": [artifact.__dict__ for artifact in manifest.artifacts],
        "messages": list(manifest.messages),
    }
