"""Recent LAS Viewer session metadata for Workbench navigation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

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
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session",
            "version": "1.0",
            "session_key": self.session_key,
            "filename": self.filename,
            "project_id": self.project_id,
            "las_id": self.las_id,
            "modified_ns": self.modified_ns,
            "valid": self.valid,
            "active": self.active,
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


class LasViewerRecentSessions:
    """Build a deterministic recent-session list from autosave metadata."""

    def __init__(self, repository: LasViewerWorkspaceAutosaveRepository) -> None:
        self.repository = repository

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
        result: list[LasViewerRecentSession] = []
        for item in self.repository.entries():
            if not include_invalid and not item.valid:
                continue
            result.append(
                self._from_repository_entry(
                    item,
                    active_project_id=active_project_id,
                    active_las_id=active_las_id,
                )
            )
            if len(result) >= int(limit):
                break
        return tuple(result)


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
            return self._from_repository_entry(item)
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
            "version": "1.0",
            "items": [item.to_dict() for item in items],
            "count": len(items),
            "renderer_neutral": True,
        }

    @staticmethod
    def _from_repository_entry(
        item: LasViewerAutosaveRepositoryEntry,
        *,
        active_project_id: str = "",
        active_las_id: str = "",
    ) -> LasViewerRecentSession:
        identity = f"{item.project_id}\0{item.las_id}\0{item.filename}".encode("utf-8")
        session_key = sha256(identity).hexdigest()[:20]
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
            reason=item.reason,
        )
