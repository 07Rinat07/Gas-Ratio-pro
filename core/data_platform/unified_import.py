"""Unified import-pipeline contracts for lightweight format plugins and previews."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
import json
from typing import Callable, Mapping

from .format_registry import DataFormatCapability, DataFormatRegistry
from .metadata_scanner import MetadataScanResult, MetadataScanner


@dataclass(frozen=True, slots=True)
class FormatPlugin:
    """A replaceable format integration described without heavy parser objects."""

    capability: DataFormatCapability
    scanner: MetadataScanner | None = None
    quick_qc: Callable[[MetadataScanResult], Mapping[str, object]] | None = None
    importer_id: str = ""
    exporter_id: str = ""

    def capability_row(self) -> dict[str, object]:
        item = self.capability
        return {
            "format_id": item.format_id,
            "display_name": item.display_name,
            "category": item.category,
            "metadata_preview": bool(item.supports_metadata_scan and self.scanner is not None),
            "quick_qc": self.quick_qc is not None,
            "import": bool(item.supports_import),
            "export": bool(item.supports_export),
            "streaming": bool(item.supports_streaming),
            "preview": bool(item.supports_preview),
            "importer_id": self.importer_id,
            "exporter_id": self.exporter_id,
        }


class FormatPluginRegistry:
    """Collision-safe plugin registry layered on the existing format registry."""

    def __init__(self, formats: DataFormatRegistry) -> None:
        self.formats = formats
        self._plugins: dict[str, FormatPlugin] = {}

    def register(self, plugin: FormatPlugin) -> None:
        format_id = plugin.capability.format_id
        registered = self.formats.require(format_id)
        if registered != plugin.capability:
            raise ValueError(f"plugin capability does not match format registry: {format_id}")
        if format_id in self._plugins:
            raise ValueError(f"format plugin already registered: {format_id}")
        self._plugins[format_id] = plugin

    def get(self, format_id: str) -> FormatPlugin | None:
        return self._plugins.get(str(format_id).strip().lower())

    def require(self, format_id: str) -> FormatPlugin:
        plugin = self.get(format_id)
        if plugin is None:
            raise KeyError(f"format plugin is not registered: {format_id}")
        return plugin

    def capability_matrix(self) -> dict[str, object]:
        rows = [self._plugins[key].capability_row() for key in sorted(self._plugins)]
        return {"schema": "gas-ratio-pro/format-capability-matrix/v1", "formats": rows}


@dataclass(frozen=True, slots=True)
class ImportProfile:
    profile_id: str
    name: str
    format_id: str
    scanner_version: str = "1"
    options: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.profile_id or not self.profile_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("profile_id must be a stable identifier")
        object.__setattr__(self, "options", dict(self.options))

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["options"] = dict(self.options)
        return payload


class ImportProfileRepository:
    """Atomic JSON storage for reusable project import profiles."""

    def __init__(self, projects_root: Path | str) -> None:
        self.projects_root = Path(projects_root)

    def save(self, project_id: str, profile: ImportProfile) -> Path:
        target = self._folder(project_id) / f"{profile.profile_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
        temp.replace(target)
        return target

    def list(self, project_id: str) -> tuple[ImportProfile, ...]:
        folder = self._folder(project_id)
        if not folder.exists():
            return ()
        items: list[ImportProfile] = []
        for path in sorted(folder.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                items.append(ImportProfile(**payload))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return tuple(items)

    def _folder(self, project_id: str) -> Path:
        project = str(project_id).strip()
        if not project or any(token in project for token in ("/", "\\", "..")):
            raise ValueError("invalid project_id")
        return self.projects_root / project / "profiles" / "import"


class ImportPreviewCache:
    """Small in-memory cache keyed by file checksum, profile and scanner version."""

    def __init__(self, max_entries: int = 32) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._entries: dict[str, dict[str, object]] = {}
        self._order: list[str] = []
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(checksum_sha256: str, profile_id: str, scanner_version: str) -> str:
        raw = f"{checksum_sha256}|{profile_id}|{scanner_version}".encode("utf-8")
        return sha256(raw).hexdigest()

    def get(self, key: str) -> dict[str, object] | None:
        value = self._entries.get(key)
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        self._order.remove(key)
        self._order.append(key)
        return json.loads(json.dumps(value, ensure_ascii=False))

    def put(self, key: str, value: Mapping[str, object]) -> None:
        payload = json.loads(json.dumps(dict(value), ensure_ascii=False))
        if key in self._entries:
            self._order.remove(key)
        self._entries[key] = payload
        self._order.append(key)
        while len(self._order) > self.max_entries:
            evicted = self._order.pop(0)
            self._entries.pop(evicted, None)

    def snapshot(self) -> dict[str, object]:
        total = self.hits + self.misses
        return {
            "entry_count": len(self._entries),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(self.hits * 100.0 / total, 2) if total else 0.0,
        }


def compute_readiness_score(*, preview_complete: bool, warning_count: int, error_count: int = 0, metadata_field_count: int = 0, qc_available: bool = False) -> dict[str, object]:
    """Return an explainable 0..100 readiness score for downstream workflows."""
    metadata_score = min(100, metadata_field_count * 10)
    preview_score = 100 if preview_complete else 40
    qc_score = 100 if qc_available and error_count == 0 else (70 if qc_available else 50)
    penalty = min(70, max(0, warning_count) * 5 + max(0, error_count) * 25)
    total = max(0, min(100, round(preview_score * 0.35 + metadata_score * 0.35 + qc_score * 0.30 - penalty)))
    return {
        "score": total,
        "status": "ready" if total >= 80 else "review" if total >= 50 else "blocked",
        "components": {"preview": preview_score, "metadata": metadata_score, "qc": qc_score},
        "warning_count": max(0, warning_count),
        "error_count": max(0, error_count),
    }
