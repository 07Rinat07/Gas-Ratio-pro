"""SQLite projection for lightweight dataset metadata queries."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .dataset_manifest import DatasetManifest


class DatasetMetadataCatalog:
    """Project-scoped SQLite projection; manifests remain the source of truth."""

    def __init__(self, projects_root: Path | str) -> None:
        self.projects_root = Path(projects_root).resolve()

    def _path(self, project_id: str) -> Path:
        if not project_id.strip() or any(ch in project_id for ch in ("/", "\\", "\x00")):
            raise ValueError("project_id must be path-safe")
        path = self.projects_root / project_id / "datasets" / "catalog.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _connect(self, project_id: str) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path(project_id))
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                lineage_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                previous_dataset_id TEXT NOT NULL,
                format_id TEXT NOT NULL,
                well_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                checksum_sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                compatibility_mode TEXT NOT NULL,
                legacy_las INTEGER NOT NULL,
                curve_count INTEGER NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_datasets_checksum ON datasets(checksum_sha256)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_datasets_lineage ON datasets(lineage_id, version)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_datasets_format ON datasets(format_id)")
        return connection

    def project(self, manifest: DatasetManifest) -> None:
        metadata = dict(manifest.metadata)
        with self._connect(manifest.project_id) as connection:
            connection.execute(
                """
                INSERT INTO datasets (
                    dataset_id, project_id, lineage_id, version, previous_dataset_id,
                    format_id, well_id, source_name, artifact_path, checksum_sha256,
                    size_bytes, created_at, compatibility_mode, legacy_las,
                    curve_count, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    metadata_json=excluded.metadata_json,
                    compatibility_mode=excluded.compatibility_mode,
                    legacy_las=excluded.legacy_las,
                    curve_count=excluded.curve_count
                """,
                (
                    manifest.dataset_id,
                    manifest.project_id,
                    manifest.lineage_id,
                    manifest.version,
                    manifest.previous_dataset_id,
                    manifest.format_id,
                    manifest.well_id,
                    manifest.source_name,
                    manifest.artifact_path,
                    manifest.checksum_sha256,
                    manifest.size_bytes,
                    manifest.created_at,
                    str(metadata.get("las_compatibility_mode", "")),
                    1 if bool(metadata.get("legacy_las", False)) else 0,
                    int(metadata.get("curve_count", 0) or 0),
                    json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                ),
            )

    def rebuild(self, project_id: str, manifests: Iterable[DatasetManifest]) -> int:
        path = self._path(project_id)
        path.unlink(missing_ok=True)
        count = 0
        for manifest in manifests:
            self.project(manifest)
            count += 1
        return count

    def snapshot(self, project_id: str) -> dict[str, object]:
        path = self._path(project_id)
        if not path.exists():
            return {"status": "empty", "dataset_count": 0, "format_count": 0, "legacy_las_count": 0}
        with self._connect(project_id) as connection:
            dataset_count = int(connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0])
            format_count = int(connection.execute("SELECT COUNT(DISTINCT format_id) FROM datasets").fetchone()[0])
            legacy_count = int(connection.execute("SELECT COUNT(*) FROM datasets WHERE legacy_las = 1").fetchone()[0])
        return {
            "status": "ok",
            "dataset_count": dataset_count,
            "format_count": format_count,
            "legacy_las_count": legacy_count,
            "database": path.name,
        }
