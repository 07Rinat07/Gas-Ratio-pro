"""Recent LAS Viewer session metadata for Workbench navigation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.las_viewer_workspace_autosave_repository import (
    LasViewerAutosaveRepositoryEntry,
    LasViewerAutosaveRepositoryRemoval,
    LasViewerWorkspaceAutosaveRepository,
)


@dataclass(frozen=True, slots=True)
class LasViewerRecentSession:
    """Compact, renderer-neutral metadata for a recent LAS session."""

    session_key: str
    filename: str
    project_id: str
    las_id: str
    modified_ns: int
    valid: bool
    active: bool = False
    pinned: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session",
            "version": "1.1",
            "session_key": self.session_key,
            "filename": self.filename,
            "project_id": self.project_id,
            "las_id": self.las_id,
            "modified_ns": self.modified_ns,
            "valid": self.valid,
            "active": self.active,
            "pinned": self.pinned,
            "reason": self.reason,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionRemoval:
    removed: bool
    session_key: str = ""
    filename: str = ""
    removed_files: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-removal",
            "version": "1.0",
            "removed": self.removed,
            "session_key": self.session_key,
            "filename": self.filename,
            "removed_files": self.removed_files,
            "reason": self.reason,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionPinResult:
    changed: bool
    session_key: str = ""
    pinned: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-pin-result",
            "version": "1.0",
            "changed": self.changed,
            "session_key": self.session_key,
            "pinned": self.pinned,
            "reason": self.reason,
            "renderer_neutral": True,
        }


class LasViewerRecentSessions:
    """Build and persist a deterministic recent-session list."""

    METADATA_FILENAME = "las-viewer-recent-sessions.json"

    def __init__(self, repository: LasViewerWorkspaceAutosaveRepository) -> None:
        self.repository = repository
        self._metadata_path = repository.directory / self.METADATA_FILENAME

    def list(
        self,
        *,
        limit: int = 10,
        include_invalid: bool = False,
        active_project_id: str = "",
        active_las_id: str = "",
    ) -> tuple[LasViewerRecentSession, ...]:
        if int(limit) < 1:
            raise ValueError("limit must be >= 1")
        pinned_keys = self._load_pinned_keys()
        result: list[LasViewerRecentSession] = []
        for item in self.repository.entries():
            if not include_invalid and not item.valid:
                continue
            result.append(
                self._from_repository_entry(
                    item,
                    active_project_id=active_project_id,
                    active_las_id=active_las_id,
                    pinned_keys=pinned_keys,
                )
            )
        result.sort(key=lambda item: (not item.pinned, -item.modified_ns, item.filename))
        return tuple(result[: int(limit)])

    def pin(self, session_key: str, *, pinned: bool = True) -> LasViewerRecentSessionPinResult:
        key = str(session_key or "").strip()
        if not key:
            return LasViewerRecentSessionPinResult(changed=False, reason="missing_session_key")
        known_keys = {item.session_key for item in self.list(limit=max(1, len(self.repository.entries()) or 1), include_invalid=True)}
        if key not in known_keys:
            return LasViewerRecentSessionPinResult(
                changed=False,
                session_key=key,
                pinned=bool(pinned),
                reason="missing_recent_session",
            )
        keys = self._load_pinned_keys()
        before = key in keys
        if pinned:
            keys.add(key)
        else:
            keys.discard(key)
        changed = before != bool(pinned)
        if changed:
            self._save_pinned_keys(keys)
        return LasViewerRecentSessionPinResult(
            changed=changed,
            session_key=key,
            pinned=bool(pinned),
            reason="updated" if changed else "unchanged",
        )

    def remove(self, session_key: str) -> LasViewerRecentSessionRemoval:
        """Remove a recent session by its stable public key."""
        key = str(session_key or "").strip()
        if not key:
            return LasViewerRecentSessionRemoval(removed=False, reason="missing_session_key")
        for item in self.repository.entries():
            recent = self._from_repository_entry(item)
            if recent.session_key != key:
                continue
            result = self.repository.remove_entry(item.filename)
            if result.removed:
                keys = self._load_pinned_keys()
                if key in keys:
                    keys.remove(key)
                    self._save_pinned_keys(keys)
            return self._removal_from_repository(key, result)
        return LasViewerRecentSessionRemoval(
            removed=False,
            session_key=key,
            reason="missing_recent_session",
        )

    @staticmethod
    def _removal_from_repository(
        session_key: str,
        result: LasViewerAutosaveRepositoryRemoval,
    ) -> LasViewerRecentSessionRemoval:
        return LasViewerRecentSessionRemoval(
            removed=result.removed,
            session_key=session_key,
            filename=result.filename,
            removed_files=result.removed_files,
            reason=result.reason,
        )

    def latest(
        self,
        *,
        project_id: str = "",
        las_id: str = "",
    ) -> LasViewerRecentSession | None:
        for item in self.repository.entries():
            if not item.valid:
                continue
            if project_id and item.project_id != project_id:
                continue
            if las_id and item.las_id != las_id:
                continue
            return self._from_repository_entry(item, pinned_keys=self._load_pinned_keys())
        return None

    def snapshot(
        self,
        *,
        limit: int = 10,
        include_invalid: bool = False,
        active_project_id: str = "",
        active_las_id: str = "",
    ) -> dict[str, object]:
        items = self.list(
            limit=limit,
            include_invalid=include_invalid,
            active_project_id=active_project_id,
            active_las_id=active_las_id,
        )
        return {
            "schema": "las.viewer.recent-sessions",
            "version": "1.1",
            "items": [item.to_dict() for item in items],
            "count": len(items),
            "pinned_count": sum(1 for item in items if item.pinned),
            "renderer_neutral": True,
        }

    @staticmethod
    def _session_key(item: LasViewerAutosaveRepositoryEntry) -> str:
        identity = f"{item.project_id}\0{item.las_id}\0{item.filename}".encode("utf-8")
        return sha256(identity).hexdigest()[:20]

    @classmethod
    def _from_repository_entry(
        cls,
        item: LasViewerAutosaveRepositoryEntry,
        *,
        active_project_id: str = "",
        active_las_id: str = "",
        pinned_keys: set[str] | None = None,
    ) -> LasViewerRecentSession:
        session_key = cls._session_key(item)
        active = bool(
            item.valid
            and item.project_id == active_project_id
            and item.las_id == active_las_id
            and (active_project_id or active_las_id)
        )
        return LasViewerRecentSession(
            session_key=session_key,
            filename=item.filename,
            project_id=item.project_id,
            las_id=item.las_id,
            modified_ns=item.modified_ns,
            valid=item.valid,
            active=active,
            pinned=session_key in (pinned_keys or set()),
            reason=item.reason,
        )

    def _load_pinned_keys(self) -> set[str]:
        if not self._metadata_path.is_file():
            return set()
        try:
            payload = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return set()
        if payload.get("schema") != "las.viewer.recent-session-preferences":
            return set()
        raw = payload.get("pinned_session_keys", [])
        if not isinstance(raw, list):
            return set()
        return {str(value).strip() for value in raw if str(value).strip()}

    def _save_pinned_keys(self, keys: set[str]) -> None:
        self.repository.directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "las.viewer.recent-session-preferences",
            "version": "1.0",
            "pinned_session_keys": sorted(keys),
            "renderer_neutral": True,
        }
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.repository.directory,
            prefix=f".{self.METADATA_FILENAME}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, self._metadata_path)
