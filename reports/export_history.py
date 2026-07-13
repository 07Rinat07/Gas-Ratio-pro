from __future__ import annotations

"""Compact, project-scoped history of successful professional exports.

Only lightweight metadata is stored. Rendered binaries, dataframes, credentials,
and full engineering payloads are intentionally excluded.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

EXPORT_HISTORY_SCHEMA = "gas-ratio-pro/export-history/v1"
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class ExportHistoryEntry:
    project_id: str
    file_name: str
    format_id: str
    format_label: str
    profile_id: str
    depth_top: float
    depth_bottom: float
    size_bytes: int
    request_signature: str = ""
    cache_hit: bool = False
    created_at: str = ""

    def normalized(self) -> "ExportHistoryEntry":
        project_id = str(self.project_id or "").strip()
        file_name = Path(str(self.file_name or "").strip()).name
        if not project_id:
            raise ValueError("project_id is required")
        if not file_name:
            raise ValueError("file_name is required")
        top = float(self.depth_top)
        bottom = float(self.depth_bottom)
        if not _is_finite(top) or not _is_finite(bottom):
            raise ValueError("depth range must be finite")
        if top > bottom:
            top, bottom = bottom, top
        return ExportHistoryEntry(
            project_id=project_id,
            file_name=file_name,
            format_id=str(self.format_id or "").strip().lower(),
            format_label=str(self.format_label or self.format_id or "").strip(),
            profile_id=str(self.profile_id or "").strip().lower(),
            depth_top=top,
            depth_bottom=bottom,
            size_bytes=max(0, int(self.size_bytes)),
            request_signature=str(self.request_signature or "").strip(),
            cache_hit=bool(self.cache_hit),
            created_at=self.created_at or datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        value = self.normalized()
        return {
            "project_id": value.project_id,
            "file_name": value.file_name,
            "format_id": value.format_id,
            "format_label": value.format_label,
            "profile_id": value.profile_id,
            "depth_top": value.depth_top,
            "depth_bottom": value.depth_bottom,
            "size_bytes": value.size_bytes,
            "request_signature": value.request_signature,
            "cache_hit": value.cache_hit,
            "created_at": value.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExportHistoryEntry":
        return cls(
            project_id=str(payload.get("project_id", "")),
            file_name=str(payload.get("file_name", "")),
            format_id=str(payload.get("format_id", "")),
            format_label=str(payload.get("format_label", "")),
            profile_id=str(payload.get("profile_id", "")),
            depth_top=float(payload.get("depth_top", 0.0)),
            depth_bottom=float(payload.get("depth_bottom", 0.0)),
            size_bytes=int(payload.get("size_bytes", 0)),
            request_signature=str(payload.get("request_signature", "")),
            cache_hit=bool(payload.get("cache_hit", False)),
            created_at=str(payload.get("created_at", "")),
        ).normalized()


@dataclass(frozen=True)
class ExportHistoryFilter:
    """Renderer-neutral filters for the compact export history."""

    search: str = ""
    format_id: str = ""
    profile_id: str = ""

    def normalized(self) -> "ExportHistoryFilter":
        return ExportHistoryFilter(
            search=str(self.search or "").strip().casefold(),
            format_id=str(self.format_id or "").strip().lower(),
            profile_id=str(self.profile_id or "").strip().lower(),
        )


def filter_export_history(
    entries: Iterable[ExportHistoryEntry],
    filters: ExportHistoryFilter | None = None,
) -> tuple[ExportHistoryEntry, ...]:
    """Return history entries matching text, format and profile filters.

    The function does not mutate repository state and is safe to reuse from
    Streamlit, desktop or CLI shells.
    """

    value = (filters or ExportHistoryFilter()).normalized()
    result: list[ExportHistoryEntry] = []
    for raw_entry in entries:
        entry = raw_entry.normalized()
        if value.format_id and entry.format_id != value.format_id:
            continue
        if value.profile_id and entry.profile_id != value.profile_id:
            continue
        if value.search:
            haystack = " ".join(
                (entry.file_name, entry.format_label, entry.profile_id, entry.created_at)
            ).casefold()
            if value.search not in haystack:
                continue
        result.append(entry)
    return tuple(result)


class ExportHistoryRepository:
    def __init__(self, root_dir: Path | str, *, max_entries: int = 20) -> None:
        self.root_dir = Path(root_dir)
        self.max_entries = max(1, int(max_entries))

    def path_for(self, project_id: str) -> Path:
        safe_id = _SAFE_ID.sub("_", str(project_id or "").strip()).strip("._")
        if not safe_id:
            raise ValueError("project_id is required")
        return self.root_dir / safe_id / "export_history.json"

    def load(self, project_id: str) -> tuple[ExportHistoryEntry, ...]:
        target = self.path_for(project_id)
        if not target.exists():
            return ()
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping) or payload.get("schema") != EXPORT_HISTORY_SCHEMA:
            raise ValueError("unsupported export history schema")
        raw_entries = payload.get("entries", ())
        if not isinstance(raw_entries, Sequence) or isinstance(raw_entries, (str, bytes, bytearray)):
            raise ValueError("invalid export history payload")
        entries = tuple(ExportHistoryEntry.from_dict(item) for item in raw_entries if isinstance(item, Mapping))
        expected_project = str(project_id).strip()
        if any(item.project_id != expected_project for item in entries):
            raise ValueError("export history belongs to another project")
        return entries[: self.max_entries]

    def record(self, entry: ExportHistoryEntry) -> Path:
        value = entry.normalized()
        try:
            existing = list(self.load(value.project_id))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            existing = []
        deduplicated = [
            item for item in existing
            if not (
                item.request_signature
                and item.request_signature == value.request_signature
                and item.file_name == value.file_name
            )
        ]
        entries = [value, *deduplicated][: self.max_entries]
        target = self.path_for(value.project_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "schema": EXPORT_HISTORY_SCHEMA,
                    "project_id": value.project_id,
                    "entries": [item.to_dict() for item in entries],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
        return target

    def clear(self, project_id: str) -> bool:
        target = self.path_for(project_id)
        if not target.exists():
            return False
        target.unlink()
        return True


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
