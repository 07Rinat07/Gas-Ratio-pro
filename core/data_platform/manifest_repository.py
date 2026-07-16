"""Atomic project-scoped persistence for lightweight dataset manifests."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .dataset_manifest import DatasetManifest


class DatasetManifestRepository:
    def __init__(self, projects_root: Path | str) -> None:
        self.projects_root = Path(projects_root).resolve()

    def _directory(self, project_id: str) -> Path:
        if not project_id.strip() or any(ch in project_id for ch in ("/", "\\", "\x00")):
            raise ValueError("project_id must be path-safe")
        return self.projects_root / project_id / "datasets" / "manifests"

    def save(self, manifest: DatasetManifest) -> Path:
        directory = self._directory(manifest.project_id)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{manifest.dataset_id}.json"
        if destination.exists():
            existing = self.load(manifest.project_id, manifest.dataset_id)
            if existing.to_dict() == manifest.to_dict():
                return destination
            raise FileExistsError(f"dataset manifest is immutable: {manifest.dataset_id}")
        self._validate_lineage(manifest)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, prefix=f".{manifest.dataset_id}.", suffix=".tmp", delete=False) as handle:
            json.dump(manifest.to_dict(), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            temp_path = Path(handle.name)
        try:
            os.replace(temp_path, destination)
        finally:
            temp_path.unlink(missing_ok=True)
        return destination

    def load(self, project_id: str, dataset_id: str) -> DatasetManifest:
        path = self._directory(project_id) / f"{dataset_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("dataset manifest must be a JSON object")
        manifest = DatasetManifest.from_dict(payload)
        if manifest.project_id != project_id or manifest.dataset_id != dataset_id:
            raise ValueError("dataset manifest identity mismatch")
        return manifest

    def list(self, project_id: str) -> tuple[DatasetManifest, ...]:
        directory = self._directory(project_id)
        if not directory.exists():
            return ()
        manifests: list[DatasetManifest] = []
        for path in sorted(directory.glob("*.json")):
            try:
                manifests.append(self.load(project_id, path.stem))
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                continue
        return tuple(manifests)


    def _validate_lineage(self, manifest: DatasetManifest) -> None:
        lineage = self.list_lineage(manifest.project_id, manifest.lineage_id)
        if not lineage:
            if manifest.version != 1 or manifest.previous_dataset_id:
                raise ValueError("first dataset lineage version must be version 1 without a previous dataset")
            return
        latest = lineage[-1]
        if manifest.version != latest.version + 1:
            raise ValueError("dataset lineage version must increment by one")
        if manifest.previous_dataset_id != latest.dataset_id:
            raise ValueError("previous_dataset_id must reference the latest lineage version")

    def find_by_checksum(self, project_id: str, checksum_sha256: str) -> tuple[DatasetManifest, ...]:
        checksum = str(checksum_sha256).strip().lower()
        return tuple(item for item in self.list(project_id) if item.checksum_sha256 == checksum)

    def list_lineage(self, project_id: str, lineage_id: str) -> tuple[DatasetManifest, ...]:
        identifier = str(lineage_id).strip()
        items = [item for item in self.list(project_id) if item.lineage_id == identifier]
        return tuple(sorted(items, key=lambda item: item.version))

    def snapshot(self, project_id: str) -> dict[str, object]:
        manifests = self.list(project_id)
        return {
            "project_id": project_id,
            "dataset_count": len(manifests),
            "total_size_bytes": sum(item.size_bytes for item in manifests),
            "formats": sorted({item.format_id for item in manifests}),
            "lineage_count": len({item.lineage_id for item in manifests}),
            "duplicate_checksum_groups": sum(1 for checksum in {item.checksum_sha256 for item in manifests} if sum(1 for item in manifests if item.checksum_sha256 == checksum) > 1),
        }
