"""Build auditable Visualization Engine asset bundles from one pipeline result.

The registry consumes an already-built ``visualization.scene.pipeline.result``
and renderer outputs produced from that same pipeline. It never rebuilds the
Domain Model, Scene, Layout or Render Model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_renderer_parity import (
    VisualizationRendererParityValidator,
    visualization_geometry_signature,
)
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


@dataclass(frozen=True, slots=True)
class VisualizationAssetEntry:
    id: str
    role: str
    format: str
    path: str
    size_bytes: int
    sha256: str
    renderer: str = ""
    geometry_signature: str = ""
    export_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "format": self.format,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "renderer": self.renderer,
            "geometry_signature": self.geometry_signature,
            "export_ready": self.export_ready,
        }


@dataclass(frozen=True, slots=True)
class VisualizationAssetRegistryResult:
    schema: str = "visualization.asset.registry"
    version: str = "1.0"
    ok: bool = False
    geometry_signature: str = ""
    render_model_version: str = ""
    compatibility_version: str = "visualization.pipeline.v1"
    assets: tuple[VisualizationAssetEntry, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "ok": self.ok,
            "geometry_signature": self.geometry_signature,
            "render_model_version": self.render_model_version,
            "compatibility_version": self.compatibility_version,
            "asset_count": len(self.assets),
            "assets": [asset.to_dict() for asset in self.assets],
            "issues": list(self.issues),
            "single_pipeline_source": True,
            "contains_raw_dataframe": False,
        }


class VisualizationAssetRegistry:
    """Render and persist SVG/PDF/JSON assets from one pipeline result."""

    def build(
        self,
        pipeline: Mapping[str, Any],
        *,
        output_dir: str | Path,
        base_name: str = "visualization",
        overwrite: bool = True,
    ) -> VisualizationAssetRegistryResult:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_name(base_name)
        issues: list[str] = []

        if str(pipeline.get("schema") or "") != "visualization.scene.pipeline.result":
            issues.append("visualization_asset_registry_unsupported_pipeline_schema")

        render_model = _mapping(pipeline.get("render_model"))
        if str(render_model.get("schema") or "") != "visualization.render.model":
            issues.append("visualization_asset_registry_render_model_missing")

        geometry_signature = visualization_geometry_signature(pipeline)
        if not geometry_signature:
            issues.append("visualization_asset_registry_geometry_signature_missing")

        svg_result = VisualizationSvgSceneRenderer().render(pipeline)
        pdf_result = VisualizationPdfRenderModelRenderer().render(pipeline)
        validator = VisualizationRendererParityValidator()
        svg_parity = validator.validate(pipeline, svg_result.to_dict()).to_dict()
        pdf_parity = validator.validate(pipeline, pdf_result.to_dict()).to_dict()
        if not svg_parity["ok"]:
            issues.append("visualization_asset_registry_svg_parity_failed")
        if not pdf_parity["ok"]:
            issues.append("visualization_asset_registry_pdf_parity_failed")

        payloads: list[tuple[str, str, str, bytes, str, bool]] = [
            (
                "preview_svg",
                "visualization_preview",
                "svg",
                svg_result.svg.encode("utf-8"),
                svg_result.renderer,
                svg_result.export_ready,
            ),
            (
                "preview_pdf",
                "visualization_preview",
                "pdf",
                pdf_result.pdf_bytes,
                pdf_result.renderer,
                pdf_result.export_ready,
            ),
            (
                "render_model",
                "render_model_contract",
                "json",
                _json_bytes(render_model),
                "",
                bool(render_model),
            ),
            (
                "geometry",
                "geometry_contract",
                "json",
                _json_bytes(
                    {
                        "schema": "visualization.geometry.asset",
                        "version": "1.0",
                        "geometry_signature": geometry_signature,
                        "render_model_width": render_model.get("width"),
                        "render_model_height": render_model.get("height"),
                        "primitive_count": len(_mapping_list(render_model.get("primitives"))),
                        "clip_count": len(_mapping_list(render_model.get("clip_regions"))),
                    }
                ),
                "",
                bool(geometry_signature),
            ),
        ]

        entries: list[VisualizationAssetEntry] = []
        for asset_id, role, format_name, content, renderer, export_ready in payloads:
            extension = format_name
            relative = f"assets/{safe_name}-{asset_id}.{extension}"
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and not overwrite:
                raise FileExistsError(f"Visualization asset already exists: {path}")
            path.write_bytes(content)
            entries.append(
                VisualizationAssetEntry(
                    id=asset_id,
                    role=role,
                    format=format_name,
                    path=relative,
                    size_bytes=len(content),
                    sha256=sha256(content).hexdigest(),
                    renderer=renderer,
                    geometry_signature=geometry_signature,
                    export_ready=bool(export_ready and content),
                )
            )

        registry_ok = not issues and all(entry.export_ready for entry in entries)
        result = VisualizationAssetRegistryResult(
            ok=registry_ok,
            geometry_signature=geometry_signature,
            render_model_version=str(render_model.get("version") or ""),
            assets=tuple(entries),
            issues=tuple(dict.fromkeys(issues)),
        )
        registry_path = output / f"{safe_name}.visualization-assets.json"
        registry_path.write_bytes(_json_bytes(result.to_dict()))
        return result


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _safe_name(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(value or "visualization"))
    text = "-".join(part for part in text.split("-") if part)
    return text or "visualization"


__all__ = [
    "VisualizationAssetEntry",
    "VisualizationAssetRegistry",
    "VisualizationAssetRegistryResult",
]
