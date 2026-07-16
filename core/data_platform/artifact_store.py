"""Project-scoped artifact storage with path containment and atomic writes."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from .checksum import sha256_file

_ALLOWED_KINDS = frozenset({"source", "derived", "preview", "exports", "cache"})


def _safe_segment(name: str, value: object) -> str:
    text = str(value).strip()
    if not text or text in {".", ".."} or any(ch in text for ch in ("/", "\\", "\x00")):
        raise ValueError(f"{name} must be a path-safe segment")
    return text


@dataclass(frozen=True, slots=True)
class ArtifactLocation:
    project_id: str
    kind: str
    relative_path: str
    size_bytes: int
    checksum_sha256: str


class ArtifactStore:
    def __init__(self, projects_root: Path | str) -> None:
        self.projects_root = Path(projects_root).resolve()

    def project_artifacts_root(self, project_id: object) -> Path:
        safe_project = _safe_segment("project_id", project_id)
        return self.projects_root / safe_project / "artifacts"

    def store_file(self, *, project_id: object, source: Path | str, kind: str = "source", filename: str | None = None) -> ArtifactLocation:
        safe_kind = str(kind).strip().lower()
        if safe_kind not in _ALLOWED_KINDS:
            raise ValueError(f"unsupported artifact kind: {kind}")
        source_path = Path(source)
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        safe_name = _safe_segment("filename", filename or source_path.name)
        destination_dir = self.project_artifacts_root(project_id) / safe_kind
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / safe_name
        with NamedTemporaryFile(dir=destination_dir, prefix=f".{safe_name}.", suffix=".tmp", delete=False) as handle:
            temp_path = Path(handle.name)
            with source_path.open("rb") as input_handle:
                shutil.copyfileobj(input_handle, handle, length=1024 * 1024)
        try:
            os.replace(temp_path, destination)
        finally:
            temp_path.unlink(missing_ok=True)
        project_root = self.project_artifacts_root(project_id)
        return ArtifactLocation(
            project_id=str(project_id).strip(),
            kind=safe_kind,
            relative_path=destination.relative_to(project_root).as_posix(),
            size_bytes=destination.stat().st_size,
            checksum_sha256=sha256_file(destination),
        )

    def resolve(self, *, project_id: object, relative_path: object) -> Path:
        root = self.project_artifacts_root(project_id).resolve()
        candidate = (root / str(relative_path)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("artifact path escapes project storage") from exc
        return candidate
