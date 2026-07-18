"""Physical-page golden artifacts for A4/A3 visual regression.

The regular visualization reference artifacts protect renderer geometry, while
this service protects the physical printing contract.  It renders the same
multi-track scene through every certified A4/A3 orientation and records every
page as SVG and PNG plus one multi-page PDF.  The manifest is deliberately
strict: a change in page size, track partition, page chrome or raster output is
visible in review instead of silently entering a release.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import struct
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree

from core.physical_print_profiles import PhysicalPrintProfile, resolve_physical_print_profile
from services.visualization_page_aware_package import VisualizationPageAwarePackageBuilder
from services.visualization_scene_pipeline import VisualizationScenePipeline


CERTIFIED_PHYSICAL_PROFILE_IDS: tuple[str, ...] = (
    "a4_portrait",
    "a4_landscape",
    "a3_portrait",
    "a3_landscape",
)


@dataclass(frozen=True, slots=True)
class PhysicalGoldenPageEntry:
    index: int
    svg_file: str
    svg_sha256: str
    png_file: str
    png_sha256: str
    width_pt: float
    height_pt: float
    png_width: int
    png_height: int
    track_ids: tuple[str, ...] = field(default_factory=tuple)
    chrome_primitive_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "svg_file": self.svg_file,
            "svg_sha256": self.svg_sha256,
            "png_file": self.png_file,
            "png_sha256": self.png_sha256,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "png_width": self.png_width,
            "png_height": self.png_height,
            "track_ids": list(self.track_ids),
            "chrome_primitive_count": self.chrome_primitive_count,
        }


@dataclass(frozen=True, slots=True)
class PhysicalGoldenProfileEntry:
    profile_id: str
    page_size: str
    orientation: str
    dpi: int
    geometry_signature: str
    parity_gate_id: str
    page_count: int
    pdf_file: str
    pdf_sha256: str
    pages: tuple[PhysicalGoldenPageEntry, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return (
            self.profile_id in CERTIFIED_PHYSICAL_PROFILE_IDS
            and self.page_count == len(self.pages)
            and self.page_count > 0
            and bool(self.geometry_signature)
            and bool(self.parity_gate_id)
            and not self.issues
        )

    def structural_signature(self) -> tuple[Any, ...]:
        """Return fields that must remain stable across an approved release."""

        return (
            self.profile_id,
            self.page_size,
            self.orientation,
            self.dpi,
            self.geometry_signature,
            self.page_count,
            tuple(
                (
                    page.index,
                    round(page.width_pt, 3),
                    round(page.height_pt, 3),
                    page.png_width,
                    page.png_height,
                    page.track_ids,
                    page.chrome_primitive_count,
                    page.svg_sha256,
                    page.png_sha256,
                )
                for page in self.pages
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "dpi": self.dpi,
            "geometry_signature": self.geometry_signature,
            "parity_gate_id": self.parity_gate_id,
            "page_count": self.page_count,
            "pdf_file": self.pdf_file,
            "pdf_sha256": self.pdf_sha256,
            "pages": [page.to_dict() for page in self.pages],
            "issues": list(self.issues),
            "ok": self.ok,
        }


@dataclass(frozen=True, slots=True)
class PhysicalGoldenManifest:
    schema: str = "visualization.physical-golden-artifacts.manifest"
    version: str = "1.0"
    source_file: str = ""
    source_sha256: str = ""
    profiles: tuple[PhysicalGoldenProfileEntry, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        ids = tuple(item.profile_id for item in self.profiles)
        return ids == CERTIFIED_PHYSICAL_PROFILE_IDS and all(item.ok for item in self.profiles)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "certified_profiles": list(CERTIFIED_PHYSICAL_PROFILE_IDS),
            "profiles": [profile.to_dict() for profile in self.profiles],
            "ok": self.ok,
            "visual_regression": True,
            "physical_page_contract": True,
            "single_pipeline_source": True,
        }


class VisualizationPhysicalGoldenArtifactService:
    """Generate and verify physical golden artifacts for certified profiles."""

    MANIFEST_NAME = "manifest.json"

    def __init__(self, builder: VisualizationPageAwarePackageBuilder | None = None) -> None:
        self._builder = builder or VisualizationPageAwarePackageBuilder()

    def generate(
        self,
        source_path: Path | str,
        output_dir: Path | str,
        *,
        profile_ids: Sequence[str] = CERTIFIED_PHYSICAL_PROFILE_IDS,
    ) -> PhysicalGoldenManifest:
        source = Path(source_path)
        source_bytes = source.read_bytes()
        base_payload = json.loads(source_bytes.decode("utf-8"))
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        entries: list[PhysicalGoldenProfileEntry] = []
        for profile_id in profile_ids:
            profile = resolve_physical_print_profile(profile_id=profile_id)
            payload = self._payload_for_profile(base_payload, profile)
            pipeline = VisualizationScenePipeline().run(payload).to_dict()
            package = self._builder.build(pipeline, raster_dpi=profile.dpi)
            profile_dir = output / profile.id
            profile_dir.mkdir(parents=True, exist_ok=True)

            pages: list[PhysicalGoldenPageEntry] = []
            issues = list(package.issues)
            for page in package.pages:
                svg_name = f"page-{page.index:02d}.svg"
                png_name = f"page-{page.index:02d}.png"
                svg_bytes = page.svg.encode("utf-8")
                png_bytes = page.png_bytes
                (profile_dir / svg_name).write_bytes(svg_bytes)
                (profile_dir / png_name).write_bytes(png_bytes)
                png_width, png_height = _png_dimensions(png_bytes)
                page_issues = _page_structural_issues(svg_bytes, png_bytes)
                issues.extend(f"{profile.id}:page-{page.index}:{item}" for item in page_issues)
                pages.append(
                    PhysicalGoldenPageEntry(
                        index=page.index,
                        svg_file=f"{profile.id}/{svg_name}",
                        svg_sha256=_sha256(svg_bytes),
                        png_file=f"{profile.id}/{png_name}",
                        png_sha256=_sha256(png_bytes),
                        width_pt=page.width_pt,
                        height_pt=page.height_pt,
                        png_width=png_width,
                        png_height=png_height,
                        track_ids=page.track_ids,
                        chrome_primitive_count=page.chrome_primitive_count,
                    )
                )

            pdf_name = f"{profile.id}.pdf"
            (profile_dir / pdf_name).write_bytes(package.pdf_bytes)
            if not package.pdf_bytes.startswith(b"%PDF-") or b"%%EOF" not in package.pdf_bytes[-2048:]:
                issues.append(f"{profile.id}:pdf_invalid")
            entries.append(
                PhysicalGoldenProfileEntry(
                    profile_id=profile.id,
                    page_size=profile.page_size,
                    orientation=profile.orientation,
                    dpi=profile.dpi,
                    geometry_signature=package.geometry_signature,
                    parity_gate_id=str(package.parity_gate.get("gate_id") or ""),
                    page_count=package.page_count,
                    pdf_file=f"{profile.id}/{pdf_name}",
                    pdf_sha256=_sha256(package.pdf_bytes),
                    pages=tuple(pages),
                    issues=tuple(dict.fromkeys(issues)),
                )
            )

        manifest = PhysicalGoldenManifest(
            source_file=source.name,
            source_sha256=_sha256(source_bytes),
            profiles=tuple(entries),
        )
        (output / self.MANIFEST_NAME).write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest

    def verify(self, artifact_dir: Path | str) -> PhysicalGoldenManifest:
        directory = Path(artifact_dir)
        payload = json.loads((directory / self.MANIFEST_NAME).read_text(encoding="utf-8"))
        if payload.get("schema") != "visualization.physical-golden-artifacts.manifest":
            raise ValueError("unsupported physical golden artifact manifest")
        if str(payload.get("version") or "") != "1.0":
            raise ValueError("unsupported physical golden artifact manifest version")

        profiles: list[PhysicalGoldenProfileEntry] = []
        for raw_profile in _mapping_list(payload.get("profiles")):
            issues: list[str] = []
            pages: list[PhysicalGoldenPageEntry] = []
            for raw_page in _mapping_list(raw_profile.get("pages")):
                svg_path = directory / str(raw_page.get("svg_file") or "")
                png_path = directory / str(raw_page.get("png_file") or "")
                try:
                    svg_bytes = svg_path.read_bytes()
                    png_bytes = png_path.read_bytes()
                except OSError:
                    issues.append(f"missing_page_artifact:{raw_page.get('index')}")
                    continue
                if _sha256(svg_bytes) != str(raw_page.get("svg_sha256") or ""):
                    issues.append(f"svg_checksum_mismatch:{raw_page.get('index')}")
                if _sha256(png_bytes) != str(raw_page.get("png_sha256") or ""):
                    issues.append(f"png_checksum_mismatch:{raw_page.get('index')}")
                issues.extend(
                    f"page-{raw_page.get('index')}:{item}"
                    for item in _page_structural_issues(svg_bytes, png_bytes)
                )
                png_width, png_height = _png_dimensions(png_bytes)
                if png_width != int(raw_page.get("png_width") or 0) or png_height != int(raw_page.get("png_height") or 0):
                    issues.append(f"png_dimensions_mismatch:{raw_page.get('index')}")
                pages.append(
                    PhysicalGoldenPageEntry(
                        index=int(raw_page.get("index") or 0),
                        svg_file=str(raw_page.get("svg_file") or ""),
                        svg_sha256=str(raw_page.get("svg_sha256") or ""),
                        png_file=str(raw_page.get("png_file") or ""),
                        png_sha256=str(raw_page.get("png_sha256") or ""),
                        width_pt=float(raw_page.get("width_pt") or 0.0),
                        height_pt=float(raw_page.get("height_pt") or 0.0),
                        png_width=png_width,
                        png_height=png_height,
                        track_ids=tuple(str(item) for item in raw_page.get("track_ids", ()) if str(item)),
                        chrome_primitive_count=int(raw_page.get("chrome_primitive_count") or 0),
                    )
                )

            pdf_path = directory / str(raw_profile.get("pdf_file") or "")
            try:
                pdf_bytes = pdf_path.read_bytes()
            except OSError:
                pdf_bytes = b""
                issues.append("missing_pdf_artifact")
            if _sha256(pdf_bytes) != str(raw_profile.get("pdf_sha256") or ""):
                issues.append("pdf_checksum_mismatch")
            if not pdf_bytes.startswith(b"%PDF-") or b"%%EOF" not in pdf_bytes[-2048:]:
                issues.append("pdf_invalid")
            profiles.append(
                PhysicalGoldenProfileEntry(
                    profile_id=str(raw_profile.get("profile_id") or ""),
                    page_size=str(raw_profile.get("page_size") or ""),
                    orientation=str(raw_profile.get("orientation") or ""),
                    dpi=int(raw_profile.get("dpi") or 0),
                    geometry_signature=str(raw_profile.get("geometry_signature") or ""),
                    parity_gate_id=str(raw_profile.get("parity_gate_id") or ""),
                    page_count=int(raw_profile.get("page_count") or 0),
                    pdf_file=str(raw_profile.get("pdf_file") or ""),
                    pdf_sha256=str(raw_profile.get("pdf_sha256") or ""),
                    pages=tuple(pages),
                    issues=tuple(dict.fromkeys(issues)),
                )
            )
        return PhysicalGoldenManifest(
            source_file=str(payload.get("source_file") or ""),
            source_sha256=str(payload.get("source_sha256") or ""),
            profiles=tuple(profiles),
        )

    @staticmethod
    def _payload_for_profile(base_payload: Mapping[str, Any], profile: PhysicalPrintProfile) -> dict[str, Any]:
        payload = json.loads(json.dumps(dict(base_payload), ensure_ascii=False))
        existing = payload.get("print_options")
        print_options = dict(existing) if isinstance(existing, Mapping) else {}
        print_options.update(
            {
                "profile_id": profile.id,
                "page_size": profile.page_size,
                "orientation": profile.orientation,
                "dpi": profile.dpi,
                "page_chrome": {
                    "enabled": True,
                    "locale": "en",
                    "title": "Gas Ratio Pro physical golden artifact",
                    "classification": "QA GOLDEN",
                    "footer_text": profile.id,
                    "repeat_legend": True,
                },
            }
        )
        payload["print_options"] = print_options
        return payload


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _sha256(value: bytes) -> str:
    return sha256(value).hexdigest()


def _png_dimensions(value: bytes) -> tuple[int, int]:
    if len(value) < 24 or value[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    return struct.unpack(">II", value[16:24])


def _page_structural_issues(svg_bytes: bytes, png_bytes: bytes) -> list[str]:
    issues: list[str] = []
    try:
        root = ElementTree.fromstring(svg_bytes.decode("utf-8"))
        if not root.tag.endswith("svg"):
            issues.append("svg_root_invalid")
        if not root.attrib.get("viewBox"):
            issues.append("svg_viewbox_missing")
    except (UnicodeDecodeError, ElementTree.ParseError):
        issues.append("svg_invalid")
    width, height = _png_dimensions(png_bytes)
    if width <= 0 or height <= 0:
        issues.append("png_invalid")
    return issues


__all__ = [
    "CERTIFIED_PHYSICAL_PROFILE_IDS",
    "PhysicalGoldenManifest",
    "PhysicalGoldenPageEntry",
    "PhysicalGoldenProfileEntry",
    "VisualizationPhysicalGoldenArtifactService",
]
