"""Reference SVG/PDF artifacts for Visualization Engine visual regression.

The service turns approved renderer-neutral fixtures into export artifacts and a
machine-readable manifest.  It belongs to the QA boundary: it does not modify
scene geometry and it does not contain UI logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree

from services.visualization_export_qa import VisualizationExportQaValidator
from services.visualization_pdf_render_model_renderer import VisualizationPdfRenderModelRenderer
from services.visualization_scene_pipeline import VisualizationScenePipeline
from services.visualization_svg_scene_renderer import VisualizationSvgSceneRenderer


@dataclass(frozen=True, slots=True)
class ReferenceArtifactEntry:
    name: str
    source_file: str
    source_sha256: str
    svg_file: str
    svg_sha256: str
    pdf_file: str
    pdf_sha256: str
    geometry_signature: str
    primitive_count: int
    clip_count: int
    track_count: int
    page_count: int
    width: int
    height: int
    width_pt: float
    height_pt: float
    font_name: str
    qa_ok: bool
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "svg_file": self.svg_file,
            "svg_sha256": self.svg_sha256,
            "pdf_file": self.pdf_file,
            "pdf_sha256": self.pdf_sha256,
            "geometry_signature": self.geometry_signature,
            "primitive_count": self.primitive_count,
            "clip_count": self.clip_count,
            "track_count": self.track_count,
            "page_count": self.page_count,
            "width": self.width,
            "height": self.height,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "font_name": self.font_name,
            "qa_ok": self.qa_ok,
            "issues": list(self.issues),
        }


@dataclass(frozen=True, slots=True)
class ReferenceArtifactManifest:
    schema: str = "visualization.reference-artifacts.manifest"
    version: str = "1.0"
    entries: tuple[ReferenceArtifactEntry, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.entries) and all(item.qa_ok and not item.issues for item in self.entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "entries": [item.to_dict() for item in self.entries],
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationReferenceArtifactService:
    """Generate and verify approved visualization reference artifacts."""

    MANIFEST_NAME = "manifest.json"

    def generate(self, fixture_paths: Sequence[Path | str], output_dir: Path | str) -> ReferenceArtifactManifest:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        entries: list[ReferenceArtifactEntry] = []

        for raw_path in fixture_paths:
            fixture_path = Path(raw_path)
            source_bytes = fixture_path.read_bytes()
            payload = json.loads(source_bytes.decode("utf-8"))
            pipeline = VisualizationScenePipeline().run(payload).to_dict()
            svg_result = VisualizationSvgSceneRenderer().render(pipeline)
            pdf_result = VisualizationPdfRenderModelRenderer().render(pipeline)
            qa = VisualizationExportQaValidator().validate(pipeline, svg_result, pdf_result)

            name = fixture_path.stem
            svg_name = f"{name}.svg"
            pdf_name = f"{name}.pdf"
            svg_bytes = svg_result.svg.encode("utf-8")
            pdf_bytes = pdf_result.pdf_bytes
            (output / svg_name).write_bytes(svg_bytes)
            (output / pdf_name).write_bytes(pdf_bytes)

            issues = list(qa.issues)
            issues.extend(self._structural_issues(svg_bytes, pdf_bytes))
            entries.append(
                ReferenceArtifactEntry(
                    name=name,
                    source_file=fixture_path.name,
                    source_sha256=_sha256(source_bytes),
                    svg_file=svg_name,
                    svg_sha256=_sha256(svg_bytes),
                    pdf_file=pdf_name,
                    pdf_sha256=_sha256(pdf_bytes),
                    geometry_signature=svg_result.geometry_signature,
                    primitive_count=svg_result.primitive_count,
                    clip_count=svg_result.clip_count,
                    track_count=svg_result.track_count,
                    page_count=pdf_result.page_count,
                    width=svg_result.width,
                    height=svg_result.height,
                    width_pt=pdf_result.width_pt,
                    height_pt=pdf_result.height_pt,
                    font_name=pdf_result.font_name,
                    qa_ok=qa.ok,
                    issues=tuple(dict.fromkeys(issues)),
                )
            )

        manifest = ReferenceArtifactManifest(entries=tuple(entries))
        self._write_manifest(output / self.MANIFEST_NAME, manifest)
        return manifest

    def verify(self, artifact_dir: Path | str) -> ReferenceArtifactManifest:
        directory = Path(artifact_dir)
        payload = json.loads((directory / self.MANIFEST_NAME).read_text(encoding="utf-8"))
        if payload.get("schema") != "visualization.reference-artifacts.manifest":
            raise ValueError("unsupported visualization reference artifact manifest")
        if str(payload.get("version") or "") != "1.0":
            raise ValueError("unsupported visualization reference artifact manifest version")

        entries: list[ReferenceArtifactEntry] = []
        for raw in _mapping_list(payload.get("entries")):
            svg_path = directory / str(raw.get("svg_file") or "")
            pdf_path = directory / str(raw.get("pdf_file") or "")
            svg_bytes = svg_path.read_bytes()
            pdf_bytes = pdf_path.read_bytes()
            issues: list[str] = []
            if _sha256(svg_bytes) != str(raw.get("svg_sha256") or ""):
                issues.append("reference_artifact_svg_checksum_mismatch")
            if _sha256(pdf_bytes) != str(raw.get("pdf_sha256") or ""):
                issues.append("reference_artifact_pdf_checksum_mismatch")
            issues.extend(self._structural_issues(svg_bytes, pdf_bytes))
            entries.append(
                ReferenceArtifactEntry(
                    name=str(raw.get("name") or ""),
                    source_file=str(raw.get("source_file") or ""),
                    source_sha256=str(raw.get("source_sha256") or ""),
                    svg_file=svg_path.name,
                    svg_sha256=str(raw.get("svg_sha256") or ""),
                    pdf_file=pdf_path.name,
                    pdf_sha256=str(raw.get("pdf_sha256") or ""),
                    geometry_signature=str(raw.get("geometry_signature") or ""),
                    primitive_count=int(raw.get("primitive_count") or 0),
                    clip_count=int(raw.get("clip_count") or 0),
                    track_count=int(raw.get("track_count") or 0),
                    page_count=int(raw.get("page_count") or 0),
                    width=int(raw.get("width") or 0),
                    height=int(raw.get("height") or 0),
                    width_pt=float(raw.get("width_pt") or 0.0),
                    height_pt=float(raw.get("height_pt") or 0.0),
                    font_name=str(raw.get("font_name") or ""),
                    qa_ok=bool(raw.get("qa_ok")) and not issues,
                    issues=tuple(dict.fromkeys(issues)),
                )
            )
        return ReferenceArtifactManifest(entries=tuple(entries))

    @staticmethod
    def structural_signature(entry: ReferenceArtifactEntry) -> tuple[Any, ...]:
        """Return stable geometry/quality fields independent of PDF metadata."""

        return (
            entry.name,
            entry.source_sha256,
            entry.geometry_signature,
            entry.primitive_count,
            entry.clip_count,
            entry.track_count,
            entry.page_count,
            entry.width,
            entry.height,
            round(entry.width_pt, 3),
            round(entry.height_pt, 3),
            bool(entry.font_name),
            entry.qa_ok,
        )

    @staticmethod
    def _write_manifest(path: Path, manifest: ReferenceArtifactManifest) -> None:
        encoded = json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path.write_text(encoded, encoding="utf-8")

    @staticmethod
    def _structural_issues(svg_bytes: bytes, pdf_bytes: bytes) -> list[str]:
        issues: list[str] = []
        try:
            root = ElementTree.fromstring(svg_bytes.decode("utf-8"))
            if not root.tag.endswith("svg"):
                issues.append("reference_artifact_svg_root_invalid")
            if not root.attrib.get("viewBox"):
                issues.append("reference_artifact_svg_viewbox_missing")
        except (UnicodeDecodeError, ElementTree.ParseError):
            issues.append("reference_artifact_svg_invalid")
        if not pdf_bytes.startswith(b"%PDF-"):
            issues.append("reference_artifact_pdf_header_invalid")
        if b"%%EOF" not in pdf_bytes[-2048:]:
            issues.append("reference_artifact_pdf_eof_missing")
        return issues


def _sha256(value: bytes) -> str:
    return sha256(value).hexdigest()


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]
