"""Recent LAS Viewer session metadata for Workbench navigation."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import io
from hashlib import sha256
import hmac
import json
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

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
class LasViewerRecentSessionPage:
    """A deterministic page of recent LAS Viewer sessions."""

    items: tuple[LasViewerRecentSession, ...]
    page: int
    page_size: int
    total_count: int
    page_count: int

    @property
    def has_previous(self) -> bool:
        return self.page > 1 and self.page_count > 0

    @property
    def has_next(self) -> bool:
        return self.page < self.page_count

    @property
    def start_index(self) -> int:
        if not self.items:
            return 0
        return (self.page - 1) * self.page_size + 1

    @property
    def end_index(self) -> int:
        if not self.items:
            return 0
        return self.start_index + len(self.items) - 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-page",
            "version": "1.0",
            "items": [item.to_dict() for item in self.items],
            "page": self.page,
            "page_size": self.page_size,
            "total_count": self.total_count,
            "page_count": self.page_count,
            "has_previous": self.has_previous,
            "has_next": self.has_next,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionGroup:
    """Renderer-neutral group of recent LAS Viewer sessions."""

    key: str
    label: str
    items: tuple[LasViewerRecentSession, ...]
    collapsed: bool = False

    @property
    def count(self) -> int:
        return len(self.items)

    @property
    def pinned_count(self) -> int:
        return sum(1 for item in self.items if item.pinned)

    @property
    def active_count(self) -> int:
        return sum(1 for item in self.items if item.active)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-group",
            "version": "1.0",
            "key": self.key,
            "label": self.label,
            "items": [item.to_dict() for item in self.items],
            "count": self.count,
            "pinned_count": self.pinned_count,
            "active_count": self.active_count,
            "collapsed": self.collapsed,
            "expanded": not self.collapsed,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionGroupPage:
    """A deterministic page of recent-session groups for Workbench navigation."""

    groups: tuple[LasViewerRecentSessionGroup, ...]
    page: int
    page_size: int
    total_group_count: int
    total_item_count: int
    page_count: int

    @property
    def has_previous(self) -> bool:
        return self.page > 1 and self.page_count > 0

    @property
    def has_next(self) -> bool:
        return self.page < self.page_count

    @property
    def start_index(self) -> int:
        if not self.groups:
            return 0
        return (self.page - 1) * self.page_size + 1

    @property
    def end_index(self) -> int:
        if not self.groups:
            return 0
        return self.start_index + len(self.groups) - 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-group-page",
            "version": "1.0",
            "groups": [group.to_dict() for group in self.groups],
            "page": self.page,
            "page_size": self.page_size,
            "total_group_count": self.total_group_count,
            "total_item_count": self.total_item_count,
            "page_count": self.page_count,
            "has_previous": self.has_previous,
            "has_next": self.has_next,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionNavigationState:
    """Persistent Workbench navigation position for grouped recent sessions."""

    group_by: str = "project"
    selected_group_key: str = ""
    selected_session_key: str = ""
    page: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-navigation-state",
            "version": "1.0",
            "group_by": self.group_by,
            "selected_group_key": self.selected_group_key,
            "selected_session_key": self.selected_session_key,
            "page": self.page,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionNavigationHistory:
    """Persistent back/forward history for recent-session navigation."""

    entries: tuple[LasViewerRecentSessionNavigationState, ...] = ()
    index: int = -1
    limit: int = 50

    @property
    def can_go_back(self) -> bool:
        return self.index > 0

    @property
    def can_go_forward(self) -> bool:
        return 0 <= self.index < len(self.entries) - 1

    @property
    def current(self) -> LasViewerRecentSessionNavigationState | None:
        if 0 <= self.index < len(self.entries):
            return self.entries[self.index]
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-navigation-history",
            "version": "1.0",
            "entries": [entry.to_dict() for entry in self.entries],
            "index": self.index,
            "limit": self.limit,
            "can_go_back": self.can_go_back,
            "can_go_forward": self.can_go_forward,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionNavigationTarget:
    """Resolved grouped-list position for a recent LAS session."""

    found: bool
    session_key: str = ""
    group_by: str = "project"
    group_key: str = ""
    page: int = 1
    group_index: int = -1
    item_index: int = -1
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-navigation-target",
            "version": "1.0",
            "found": self.found,
            "session_key": self.session_key,
            "group_by": self.group_by,
            "group_key": self.group_key,
            "page": self.page,
            "group_index": self.group_index,
            "item_index": self.item_index,
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


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionBookmark:
    """Named renderer-neutral shortcut to a recent LAS session."""

    session_key: str
    label: str
    folder: str = ""
    position: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-bookmark",
            "version": "1.1",
            "session_key": self.session_key,
            "label": self.label,
            "folder": self.folder,
            "position": self.position,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionBookmarkTrashItem:
    """Recoverable bookmark removed from the active bookmark collection."""

    session_key: str
    label: str
    folder: str = ""
    position: int = 0
    deletion_order: int = 0
    deleted_at_ns: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-bookmark-trash-item",
            "version": "1.0",
            "session_key": self.session_key,
            "label": self.label,
            "folder": self.folder,
            "position": self.position,
            "deletion_order": self.deletion_order,
            "deleted_at_ns": self.deleted_at_ns,
            "renderer_neutral": True,
        }






@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionBookmarkTrashEvent:
    """Persistent audit event for bookmark trash operations."""

    action: str
    session_key: str
    label: str = ""
    occurred_at_ns: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-bookmark-trash-event",
            "version": "1.0",
            "action": self.action,
            "session_key": self.session_key,
            "label": self.label,
            "occurred_at_ns": self.occurred_at_ns,
            "reason": self.reason,
            "renderer_neutral": True,
        }




@dataclass(frozen=True, slots=True)
class LasViewerAuditJournalSignatureEvent:
    """Persistent audit record for signed journal verification attempts."""

    source: str
    operation: str
    accepted: bool
    signer_id: str = ""
    key_id: str = ""
    reason: str = ""
    occurred_at_ns: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.audit-journal-signature-event",
            "version": "1.0",
            "source": self.source,
            "operation": self.operation,
            "accepted": self.accepted,
            "signer_id": self.signer_id,
            "key_id": self.key_id,
            "reason": self.reason,
            "occurred_at_ns": self.occurred_at_ns,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionBookmarkTrashRetention:
    """Persistent automatic cleanup policy for recoverable bookmarks."""

    enabled: bool = False
    retention_days: float = 30.0
    last_cleanup_ns: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-bookmark-trash-retention",
            "version": "1.0",
            "enabled": self.enabled,
            "retention_days": self.retention_days,
            "last_cleanup_ns": self.last_cleanup_ns,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionBookmarkExchangeResult:
    imported: int = 0
    skipped: int = 0
    conflicts: int = 0
    missing_sessions: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-bookmark-exchange-result",
            "version": "1.0",
            "imported": self.imported,
            "skipped": self.skipped,
            "conflicts": self.conflicts,
            "missing_sessions": self.missing_sessions,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerRecentSessionBookmarkResult:
    changed: bool
    session_key: str = ""
    label: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "las.viewer.recent-session-bookmark-result",
            "version": "1.0",
            "changed": self.changed,
            "session_key": self.session_key,
            "label": self.label,
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
        query: str = "",
        project_id: str = "",
        las_id: str = "",
        pinned_only: bool = False,
        active_only: bool = False,
        sort_by: str = "modified",
        sort_order: str = "desc",
        pinned_first: bool = True,
    ) -> tuple[LasViewerRecentSession, ...]:
        if int(limit) < 1:
            raise ValueError("limit must be >= 1")
        result = self._filtered_sorted_items(
            include_invalid=include_invalid,
            active_project_id=active_project_id,
            active_las_id=active_las_id,
            query=query,
            project_id=project_id,
            las_id=las_id,
            pinned_only=pinned_only,
            active_only=active_only,
            sort_by=sort_by,
            sort_order=sort_order,
            pinned_first=pinned_first,
        )
        return tuple(result[: int(limit)])

    def paginate(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        include_invalid: bool = False,
        active_project_id: str = "",
        active_las_id: str = "",
        query: str = "",
        project_id: str = "",
        las_id: str = "",
        pinned_only: bool = False,
        active_only: bool = False,
        sort_by: str = "modified",
        sort_order: str = "desc",
        pinned_first: bool = True,
    ) -> LasViewerRecentSessionPage:
        normalized_page = int(page)
        normalized_page_size = int(page_size)
        if normalized_page < 1:
            raise ValueError("page must be >= 1")
        if normalized_page_size < 1:
            raise ValueError("page_size must be >= 1")

        result = self._filtered_sorted_items(
            include_invalid=include_invalid,
            active_project_id=active_project_id,
            active_las_id=active_las_id,
            query=query,
            project_id=project_id,
            las_id=las_id,
            pinned_only=pinned_only,
            active_only=active_only,
            sort_by=sort_by,
            sort_order=sort_order,
            pinned_first=pinned_first,
        )
        total_count = len(result)
        page_count = (total_count + normalized_page_size - 1) // normalized_page_size
        start = (normalized_page - 1) * normalized_page_size
        items = tuple(result[start : start + normalized_page_size])
        return LasViewerRecentSessionPage(
            items=items,
            page=normalized_page,
            page_size=normalized_page_size,
            total_count=total_count,
            page_count=page_count,
        )

    def _filtered_sorted_items(
        self,
        *,
        include_invalid: bool,
        active_project_id: str,
        active_las_id: str,
        query: str,
        project_id: str,
        las_id: str,
        pinned_only: bool,
        active_only: bool,
        sort_by: str,
        sort_order: str,
        pinned_first: bool,
    ) -> list[LasViewerRecentSession]:
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
        normalized_query = str(query or "").strip().casefold()
        normalized_project_id = str(project_id or "").strip()
        normalized_las_id = str(las_id or "").strip()
        result = [
            item
            for item in result
            if self._matches_filters(
                item,
                query=normalized_query,
                project_id=normalized_project_id,
                las_id=normalized_las_id,
                pinned_only=bool(pinned_only),
                active_only=bool(active_only),
            )
        ]
        normalized_sort_by = str(sort_by or "modified").strip().lower()
        normalized_sort_order = str(sort_order or "desc").strip().lower()
        if normalized_sort_by not in {"modified", "filename", "project", "las_id"}:
            raise ValueError("sort_by must be one of: modified, filename, project, las_id")
        if normalized_sort_order not in {"asc", "desc"}:
            raise ValueError("sort_order must be either asc or desc")
        return self._sort_items(
            result,
            sort_by=normalized_sort_by,
            sort_order=normalized_sort_order,
            pinned_first=bool(pinned_first),
        )


    def group(
        self,
        *,
        group_by: str = "project",
        include_invalid: bool = False,
        active_project_id: str = "",
        active_las_id: str = "",
        query: str = "",
        project_id: str = "",
        las_id: str = "",
        pinned_only: bool = False,
        active_only: bool = False,
        sort_by: str = "modified",
        sort_order: str = "desc",
        pinned_first: bool = True,
    ) -> tuple[LasViewerRecentSessionGroup, ...]:
        """Group filtered recent sessions without changing item ordering."""
        normalized_group_by = str(group_by or "project").strip().lower()
        if normalized_group_by not in {"project", "las_id", "status"}:
            raise ValueError("group_by must be one of: project, las_id, status")
        items = self._filtered_sorted_items(
            include_invalid=include_invalid,
            active_project_id=active_project_id,
            active_las_id=active_las_id,
            query=query,
            project_id=project_id,
            las_id=las_id,
            pinned_only=pinned_only,
            active_only=active_only,
            sort_by=sort_by,
            sort_order=sort_order,
            pinned_first=pinned_first,
        )
        buckets: dict[str, list[LasViewerRecentSession]] = {}
        labels: dict[str, str] = {}
        for item in items:
            if normalized_group_by == "project":
                key = item.project_id or "unassigned"
                label = item.project_id or "Unassigned"
            elif normalized_group_by == "las_id":
                key = item.las_id or "unknown"
                label = item.las_id or "Unknown LAS"
            else:
                key = "active" if item.active else "pinned" if item.pinned else "recent"
                label = key.capitalize()
            buckets.setdefault(key, []).append(item)
            labels[key] = label
        collapsed_groups = self._load_collapsed_groups()
        return tuple(
            LasViewerRecentSessionGroup(
                key=key,
                label=labels[key],
                items=tuple(group_items),
                collapsed=f"{normalized_group_by}:{key}" in collapsed_groups,
            )
            for key, group_items in buckets.items()
        )


    def paginate_groups(
        self,
        *,
        group_by: str = "project",
        page: int = 1,
        page_size: int = 10,
        include_invalid: bool = False,
        active_project_id: str = "",
        active_las_id: str = "",
        query: str = "",
        project_id: str = "",
        las_id: str = "",
        pinned_only: bool = False,
        active_only: bool = False,
        sort_by: str = "modified",
        sort_order: str = "desc",
        pinned_first: bool = True,
    ) -> LasViewerRecentSessionGroupPage:
        """Paginate grouped recent sessions after filtering and sorting items."""
        normalized_page = int(page)
        normalized_page_size = int(page_size)
        if normalized_page < 1:
            raise ValueError("page must be >= 1")
        if normalized_page_size < 1:
            raise ValueError("page_size must be >= 1")

        groups = self.group(
            group_by=group_by,
            include_invalid=include_invalid,
            active_project_id=active_project_id,
            active_las_id=active_las_id,
            query=query,
            project_id=project_id,
            las_id=las_id,
            pinned_only=pinned_only,
            active_only=active_only,
            sort_by=sort_by,
            sort_order=sort_order,
            pinned_first=pinned_first,
        )
        total_group_count = len(groups)
        total_item_count = sum(group.count for group in groups)
        page_count = (total_group_count + normalized_page_size - 1) // normalized_page_size
        start = (normalized_page - 1) * normalized_page_size
        return LasViewerRecentSessionGroupPage(
            groups=tuple(groups[start : start + normalized_page_size]),
            page=normalized_page,
            page_size=normalized_page_size,
            total_group_count=total_group_count,
            total_item_count=total_item_count,
            page_count=page_count,
        )


    def set_group_collapsed(
        self,
        group_by: str,
        group_key: str,
        *,
        collapsed: bool = True,
    ) -> bool:
        """Persist collapsed state for a recent-session group."""
        normalized_group_by = str(group_by or "").strip().lower()
        if normalized_group_by not in {"project", "las_id", "status"}:
            raise ValueError("group_by must be one of: project, las_id, status")
        normalized_key = str(group_key or "").strip()
        if not normalized_key:
            raise ValueError("group_key must not be empty")
        token = f"{normalized_group_by}:{normalized_key}"
        collapsed_groups = self._load_collapsed_groups()
        before = token in collapsed_groups
        if collapsed:
            collapsed_groups.add(token)
        else:
            collapsed_groups.discard(token)
        changed = before != bool(collapsed)
        if changed:
            self._save_preferences(
                pinned_keys=self._load_pinned_keys(),
                collapsed_groups=collapsed_groups,
                navigation_state=self.navigation_state(),
                navigation_history=self.navigation_history(),
            )
        return changed

    def toggle_group_collapsed(self, group_by: str, group_key: str) -> bool:
        """Toggle and return the new collapsed state for a group."""
        normalized_group_by = str(group_by or "").strip().lower()
        normalized_key = str(group_key or "").strip()
        if normalized_group_by not in {"project", "las_id", "status"}:
            raise ValueError("group_by must be one of: project, las_id, status")
        if not normalized_key:
            raise ValueError("group_key must not be empty")
        token = f"{normalized_group_by}:{normalized_key}"
        collapsed_groups = self._load_collapsed_groups()
        new_state = token not in collapsed_groups
        self.set_group_collapsed(normalized_group_by, normalized_key, collapsed=new_state)
        return new_state

    def navigation_state(self) -> LasViewerRecentSessionNavigationState:
        """Load the last persisted grouped-list navigation position."""
        payload = self._load_preferences()
        raw = payload.get("navigation_state", {})
        if not isinstance(raw, dict):
            raw = {}
        group_by = str(raw.get("group_by", "project") or "project").strip().lower()
        if group_by not in {"project", "las_id", "status"}:
            group_by = "project"
        try:
            page = max(1, int(raw.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        return LasViewerRecentSessionNavigationState(
            group_by=group_by,
            selected_group_key=str(raw.get("selected_group_key", "") or "").strip(),
            selected_session_key=str(raw.get("selected_session_key", "") or "").strip(),
            page=page,
        )

    def set_navigation_state(
        self,
        *,
        group_by: str,
        selected_group_key: str = "",
        selected_session_key: str = "",
        page: int = 1,
        record_history: bool = True,
    ) -> LasViewerRecentSessionNavigationState:
        """Persist the current Workbench group, selection, and page."""
        normalized_group_by = str(group_by or "project").strip().lower()
        if normalized_group_by not in {"project", "las_id", "status"}:
            raise ValueError("group_by must be one of: project, las_id, status")
        normalized_page = int(page)
        if normalized_page < 1:
            raise ValueError("page must be >= 1")
        state = LasViewerRecentSessionNavigationState(
            group_by=normalized_group_by,
            selected_group_key=str(selected_group_key or "").strip(),
            selected_session_key=str(selected_session_key or "").strip(),
            page=normalized_page,
        )
        history = self.navigation_history()
        if record_history:
            history = self._append_navigation_history(history, state)
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=state,
            navigation_history=history,
        )
        return state

    def navigation_history(self) -> LasViewerRecentSessionNavigationHistory:
        payload = self._load_preferences()
        raw = payload.get("navigation_history", {})
        if not isinstance(raw, dict):
            raw = {}
        try:
            limit = min(200, max(1, int(raw.get("limit", 50))))
        except (TypeError, ValueError):
            limit = 50
        entries: list[LasViewerRecentSessionNavigationState] = []
        for item in raw.get("entries", []) if isinstance(raw.get("entries", []), list) else []:
            if not isinstance(item, dict):
                continue
            group_by = str(item.get("group_by", "project") or "project").strip().lower()
            if group_by not in {"project", "las_id", "status"}:
                continue
            try:
                page = max(1, int(item.get("page", 1)))
            except (TypeError, ValueError):
                page = 1
            entries.append(LasViewerRecentSessionNavigationState(
                group_by=group_by,
                selected_group_key=str(item.get("selected_group_key", "") or "").strip(),
                selected_session_key=str(item.get("selected_session_key", "") or "").strip(),
                page=page,
            ))
        entries = entries[-limit:]
        try:
            index = int(raw.get("index", len(entries) - 1))
        except (TypeError, ValueError):
            index = len(entries) - 1
        index = min(max(index, -1), len(entries) - 1)
        return LasViewerRecentSessionNavigationHistory(tuple(entries), index, limit)

    def navigate_back(self) -> LasViewerRecentSessionNavigationState | None:
        history = self.navigation_history()
        if not history.can_go_back:
            return None
        updated = LasViewerRecentSessionNavigationHistory(history.entries, history.index - 1, history.limit)
        state = updated.current
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=state,
            navigation_history=updated,
        )
        return state

    def navigate_forward(self) -> LasViewerRecentSessionNavigationState | None:
        history = self.navigation_history()
        if not history.can_go_forward:
            return None
        updated = LasViewerRecentSessionNavigationHistory(history.entries, history.index + 1, history.limit)
        state = updated.current
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=state,
            navigation_history=updated,
        )
        return state

    @staticmethod
    def _append_navigation_history(
        history: LasViewerRecentSessionNavigationHistory,
        state: LasViewerRecentSessionNavigationState,
    ) -> LasViewerRecentSessionNavigationHistory:
        if history.current == state:
            return history
        entries = list(history.entries[: history.index + 1])
        entries.append(state)
        entries = entries[-history.limit :]
        return LasViewerRecentSessionNavigationHistory(tuple(entries), len(entries) - 1, history.limit)


    def locate_session(
        self,
        session_key: str,
        *,
        group_by: str = "project",
        page_size: int = 10,
        include_invalid: bool = False,
        active_project_id: str = "",
        active_las_id: str = "",
        query: str = "",
        project_id: str = "",
        las_id: str = "",
        pinned_only: bool = False,
        active_only: bool = False,
        sort_by: str = "modified",
        sort_order: str = "desc",
        pinned_first: bool = True,
        persist: bool = False,
    ) -> LasViewerRecentSessionNavigationTarget:
        """Resolve a session to its grouped page and optional persisted selection."""
        key = str(session_key or "").strip()
        normalized_group_by = str(group_by or "project").strip().lower()
        normalized_page_size = int(page_size)
        if normalized_group_by not in {"project", "las_id", "status"}:
            raise ValueError("group_by must be one of: project, las_id, status")
        if normalized_page_size < 1:
            raise ValueError("page_size must be >= 1")
        if not key:
            return LasViewerRecentSessionNavigationTarget(
                found=False, group_by=normalized_group_by, reason="missing_session_key"
            )

        groups = self.group(
            group_by=normalized_group_by,
            include_invalid=include_invalid,
            active_project_id=active_project_id,
            active_las_id=active_las_id,
            query=query,
            project_id=project_id,
            las_id=las_id,
            pinned_only=pinned_only,
            active_only=active_only,
            sort_by=sort_by,
            sort_order=sort_order,
            pinned_first=pinned_first,
        )
        for group_index, group in enumerate(groups):
            for item_index, item in enumerate(group.items):
                if item.session_key != key:
                    continue
                page = group_index // normalized_page_size + 1
                target = LasViewerRecentSessionNavigationTarget(
                    found=True,
                    session_key=key,
                    group_by=normalized_group_by,
                    group_key=group.key,
                    page=page,
                    group_index=group_index,
                    item_index=item_index,
                    reason="resolved",
                )
                if persist:
                    self.set_navigation_state(
                        group_by=normalized_group_by,
                        selected_group_key=group.key,
                        selected_session_key=key,
                        page=page,
                    )
                return target
        return LasViewerRecentSessionNavigationTarget(
            found=False,
            session_key=key,
            group_by=normalized_group_by,
            reason="missing_recent_session",
        )

    def focus_latest(
        self,
        *,
        group_by: str = "project",
        page_size: int = 10,
        project_id: str = "",
        las_id: str = "",
    ) -> LasViewerRecentSessionNavigationTarget:
        """Persist navigation to the newest valid session matching optional identifiers."""
        item = self.latest(project_id=project_id, las_id=las_id)
        if item is None:
            return LasViewerRecentSessionNavigationTarget(
                found=False,
                group_by=str(group_by or "project").strip().lower(),
                reason="missing_recent_session",
            )
        return self.locate_session(
            item.session_key,
            group_by=group_by,
            page_size=page_size,
            persist=True,
        )



    def bookmarks(
        self,
        *,
        folder: str | None = None,
        sort_by: str = "position",
        sort_order: str = "asc",
    ) -> tuple[LasViewerRecentSessionBookmark, ...]:
        """Return persistent shortcuts, optionally filtered by folder and sorted."""
        normalized_sort = str(sort_by or "position").strip().lower()
        normalized_order = str(sort_order or "asc").strip().lower()
        if normalized_sort not in {"position", "label", "folder"}:
            raise ValueError("sort_by must be one of: position, label, folder")
        if normalized_order not in {"asc", "desc"}:
            raise ValueError("sort_order must be either asc or desc")
        known = {item.session_key for item in self.list(limit=max(1, len(self.repository.entries()) or 1), include_invalid=True)}
        raw = self._load_bookmarks()
        items = [
            LasViewerRecentSessionBookmark(
                session_key=key,
                label=str(value.get("label", "")),
                folder=str(value.get("folder", "")),
                position=int(value.get("position", 0)),
            )
            for key, value in raw.items()
            if key in known
        ]
        if folder is not None:
            normalized_folder = str(folder or "").strip()
            items = [item for item in items if item.folder == normalized_folder]
        key_functions = {
            "position": lambda item: (item.position, item.label.casefold(), item.session_key),
            "label": lambda item: (item.label.casefold(), item.folder.casefold(), item.session_key),
            "folder": lambda item: (item.folder.casefold(), item.position, item.label.casefold(), item.session_key),
        }
        items.sort(key=key_functions[normalized_sort], reverse=normalized_order == "desc")
        return tuple(items)

    def bookmark_folders(self) -> tuple[str, ...]:
        """Return normalized non-empty bookmark folders in deterministic order."""
        return tuple(sorted({item.folder for item in self.bookmarks() if item.folder}, key=str.casefold))

    def export_bookmarks(self, path: str | Path | None = None) -> dict[str, object]:
        """Export portable bookmark metadata, optionally using an atomic JSON write."""
        recent = {item.session_key: item for item in self.list(limit=max(1, len(self.repository.entries()) or 1), include_invalid=True)}
        payload = {
            "schema": "las.viewer.recent-session-bookmark-exchange",
            "version": "1.0",
            "bookmarks": [
                {
                    **bookmark.to_dict(),
                    "project_id": recent.get(bookmark.session_key).project_id if recent.get(bookmark.session_key) else "",
                    "las_id": recent.get(bookmark.session_key).las_id if recent.get(bookmark.session_key) else "",
                    "filename": recent.get(bookmark.session_key).filename if recent.get(bookmark.session_key) else "",
                }
                for bookmark in self.bookmarks()
            ],
            "renderer_neutral": True,
        }
        if path is not None:
            destination = Path(path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=destination.parent,
                prefix=f".{destination.name}.", suffix=".tmp", delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            os.replace(temporary, destination)
        return payload

    def backup_bookmarks(self, path: str | Path) -> dict[str, object]:
        """Create a portable ZIP backup with an integrity manifest."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = self.export_bookmarks()
        bookmark_bytes = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest = sha256(bookmark_bytes).hexdigest()
        manifest = {
            "schema": "las.viewer.recent-session-bookmark-backup",
            "version": "1.0",
            "payload": "bookmarks.json",
            "sha256": digest,
            "renderer_neutral": True,
        }
        with NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        try:
            with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(
                    "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                )
                archive.writestr("bookmarks.json", bookmark_bytes)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return manifest

    def restore_bookmark_backup(
        self,
        path: str | Path,
        *,
        conflict: str = "skip",
    ) -> LasViewerRecentSessionBookmarkExchangeResult:
        """Validate and restore bookmarks from a trusted backup archive."""
        source = Path(path)
        try:
            with ZipFile(source, "r") as archive:
                names = set(archive.namelist())
                if names != {"manifest.json", "bookmarks.json"}:
                    raise ValueError("invalid bookmark backup contents")
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                if manifest.get("schema") != "las.viewer.recent-session-bookmark-backup":
                    raise ValueError("unsupported bookmark backup schema")
                if str(manifest.get("version", "")) != "1.0":
                    raise ValueError("unsupported bookmark backup version")
                if manifest.get("renderer_neutral") is not True:
                    raise ValueError("incompatible bookmark backup contract")
                bookmark_bytes = archive.read("bookmarks.json")
        except (BadZipFile, KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid bookmark backup archive") from exc
        expected = str(manifest.get("sha256", "")).strip().lower()
        actual = sha256(bookmark_bytes).hexdigest()
        if not expected or expected != actual:
            raise ValueError("bookmark backup checksum mismatch")
        try:
            payload = json.loads(bookmark_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid bookmark backup payload") from exc
        return self.import_bookmarks(payload, conflict=conflict)

    @staticmethod
    def migrate_bookmark_exchange(payload: dict[str, object]) -> dict[str, object]:
        """Return the current bookmark exchange contract without mutating input."""
        if not isinstance(payload, dict):
            raise ValueError("bookmark exchange payload must be an object")
        schema = payload.get("schema")
        version = str(payload.get("version", "")).strip()
        if schema != "las.viewer.recent-session-bookmark-exchange":
            raise ValueError("unsupported bookmark exchange schema")
        if payload.get("renderer_neutral") is not True:
            raise ValueError("incompatible bookmark exchange contract")
        if version == "1.0":
            return json.loads(json.dumps(payload))
        if version != "0.9":
            raise ValueError(f"unsupported bookmark exchange version: {version or 'missing'}")

        legacy_records = payload.get("items", payload.get("bookmarks", []))
        if not isinstance(legacy_records, list):
            raise ValueError("legacy bookmark items must be a list")
        migrated: list[dict[str, object]] = []
        for index, record in enumerate(legacy_records):
            if not isinstance(record, dict):
                raise ValueError(f"bookmark record {index} must be an object")
            migrated.append({
                "schema": "las.viewer.recent-session-bookmark",
                "version": "1.1",
                "session_key": str(record.get("session_key", record.get("key", ""))).strip(),
                "label": str(record.get("label", record.get("name", ""))).strip(),
                "folder": str(record.get("folder", record.get("group", "")) or "").strip(),
                "position": record.get("position", record.get("order", index)),
                "project_id": str(record.get("project_id", "")).strip(),
                "las_id": str(record.get("las_id", "")).strip(),
                "filename": str(record.get("filename", "")).strip(),
                "renderer_neutral": True,
            })
        return {
            "schema": "las.viewer.recent-session-bookmark-exchange",
            "version": "1.0",
            "bookmarks": migrated,
            "renderer_neutral": True,
        }

    @staticmethod
    def validate_bookmark_exchange(payload: dict[str, object]) -> tuple[str, ...]:
        """Validate the current exchange contract and return deterministic diagnostics."""
        current = LasViewerRecentSessions.migrate_bookmark_exchange(payload)
        records = current.get("bookmarks", [])
        if not isinstance(records, list):
            raise ValueError("bookmarks must be a list")
        diagnostics: list[str] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(f"bookmark record {index} must be an object")
            label = str(record.get("label", "")).strip()
            identity = any(str(record.get(name, "")).strip() for name in ("session_key", "las_id", "filename"))
            if not identity:
                raise ValueError(f"bookmark record {index} has no session identity")
            if not label:
                diagnostics.append(f"bookmark_label_fallback:{index}")
            try:
                position = int(record.get("position", index))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"bookmark record {index} has invalid position") from exc
            if position < 0:
                raise ValueError(f"bookmark record {index} has negative position")
        return tuple(diagnostics)

    def import_bookmarks(
        self,
        source: dict[str, object] | str | Path,
        *,
        conflict: str = "skip",
    ) -> LasViewerRecentSessionBookmarkExchangeResult:
        """Import portable bookmarks and resolve sessions by key or LAS identity."""
        policy = str(conflict or "skip").strip().lower()
        if policy not in {"skip", "overwrite", "error"}:
            raise ValueError("conflict must be one of: skip, overwrite, error")
        if isinstance(source, (str, Path)):
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
        else:
            payload = source
        payload = self.migrate_bookmark_exchange(payload)
        self.validate_bookmark_exchange(payload)
        records = payload.get("bookmarks", [])
        if not isinstance(records, list):
            raise ValueError("bookmarks must be a list")

        recent_items = self.list(limit=max(1, len(self.repository.entries()) or 1), include_invalid=True)
        by_key = {item.session_key: item for item in recent_items}
        by_identity = {(item.project_id, item.las_id): item for item in recent_items}
        by_filename = {item.filename: item for item in recent_items}
        current = self._load_bookmarks()
        updated = dict(current)
        imported = skipped = conflicts = missing = 0

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                skipped += 1
                continue
            key = str(record.get("session_key", "")).strip()
            item = by_key.get(key)
            if item is None:
                identity = (str(record.get("project_id", "")).strip(), str(record.get("las_id", "")).strip())
                item = by_identity.get(identity) if any(identity) else None
            if item is None:
                item = by_filename.get(str(record.get("filename", "")).strip())
            if item is None:
                missing += 1
                continue
            key = item.session_key
            exists = key in updated
            if exists and policy == "error":
                raise ValueError(f"bookmark conflict: {key}")
            if exists and policy == "skip":
                conflicts += 1
                skipped += 1
                continue
            label = str(record.get("label", "")).strip() or item.las_id or item.filename
            folder = str(record.get("folder", "") or "").strip()
            try:
                position = max(0, int(record.get("position", index)))
            except (TypeError, ValueError):
                position = index
            updated[key] = {"label": label, "folder": folder, "position": position}
            imported += 1
            conflicts += int(exists)

        if updated != current:
            self._save_preferences(
                pinned_keys=self._load_pinned_keys(),
                collapsed_groups=self._load_collapsed_groups(),
                navigation_state=self.navigation_state(),
                navigation_history=self.navigation_history(),
                bookmarks=updated,
            )
        return LasViewerRecentSessionBookmarkExchangeResult(imported, skipped, conflicts, missing)

    def set_bookmark(
        self,
        session_key: str,
        *,
        label: str = "",
        folder: str = "",
        position: int | None = None,
    ) -> LasViewerRecentSessionBookmarkResult:
        """Create or rename a persistent shortcut to a recent LAS session."""
        key = str(session_key or "").strip()
        if not key:
            return LasViewerRecentSessionBookmarkResult(False, reason="missing_session_key")
        items = self.list(limit=max(1, len(self.repository.entries()) or 1), include_invalid=True)
        item = next((value for value in items if value.session_key == key), None)
        if item is None:
            return LasViewerRecentSessionBookmarkResult(False, session_key=key, reason="missing_recent_session")
        normalized_label = str(label or "").strip() or item.las_id or item.filename
        bookmarks = self._load_bookmarks()
        previous = bookmarks.get(key, {})
        normalized_folder = str(folder or "").strip()
        if position is None:
            normalized_position = int(previous.get("position", len(bookmarks)))
        else:
            normalized_position = int(position)
            if normalized_position < 0:
                raise ValueError("position must be >= 0")
        updated = {
            "label": normalized_label,
            "folder": normalized_folder,
            "position": normalized_position,
        }
        changed = previous != updated
        bookmarks[key] = updated
        if changed:
            self._save_preferences(
                pinned_keys=self._load_pinned_keys(),
                collapsed_groups=self._load_collapsed_groups(),
                navigation_state=self.navigation_state(),
                navigation_history=self.navigation_history(),
                bookmarks=bookmarks,
            )
        return LasViewerRecentSessionBookmarkResult(
            changed=changed,
            session_key=key,
            label=normalized_label,
            reason="updated" if changed else "unchanged",
        )

    def remove_bookmark(self, session_key: str) -> LasViewerRecentSessionBookmarkResult:
        key = str(session_key or "").strip()
        if not key:
            return LasViewerRecentSessionBookmarkResult(False, reason="missing_session_key")
        bookmarks = self._load_bookmarks()
        removed = bookmarks.pop(key, None)
        if removed is None:
            return LasViewerRecentSessionBookmarkResult(False, session_key=key, reason="missing_bookmark")
        trash = self._load_bookmark_trash()
        next_order = max((int(value.get("deletion_order", 0)) for value in trash.values()), default=0) + 1
        trash[key] = {
            "label": str(removed.get("label", "")),
            "folder": str(removed.get("folder", "")),
            "position": int(removed.get("position", 0)),
            "deletion_order": next_order,
            "deleted_at_ns": time.time_ns(),
        }
        label = str(removed.get("label", ""))
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            bookmarks=bookmarks,
            bookmark_trash=trash,
            bookmark_trash_journal=self._append_bookmark_trash_event("removed", key, label),
        )
        return LasViewerRecentSessionBookmarkResult(True, key, label, "removed")

    def bookmark_trash(self) -> tuple[LasViewerRecentSessionBookmarkTrashItem, ...]:
        """Return recoverable removed bookmarks, newest deletion first."""
        raw = self._load_bookmark_trash()
        items = [
            LasViewerRecentSessionBookmarkTrashItem(
                session_key=key,
                label=str(value.get("label", "")),
                folder=str(value.get("folder", "")),
                position=int(value.get("position", 0)),
                deletion_order=int(value.get("deletion_order", 0)),
                deleted_at_ns=int(value.get("deleted_at_ns", 0)),
            )
            for key, value in raw.items()
        ]
        items.sort(key=lambda item: (-item.deletion_order, item.label.casefold(), item.session_key))
        return tuple(items)

    def restore_bookmark(self, session_key: str) -> LasViewerRecentSessionBookmarkResult:
        """Restore a removed bookmark when its recent LAS session still exists."""
        key = str(session_key or "").strip()
        if not key:
            return LasViewerRecentSessionBookmarkResult(False, reason="missing_session_key")
        trash = self._load_bookmark_trash()
        removed = trash.get(key)
        if removed is None:
            return LasViewerRecentSessionBookmarkResult(False, session_key=key, reason="missing_trash_item")
        known = {item.session_key for item in self.list(limit=max(1, len(self.repository.entries()) or 1), include_invalid=True)}
        if key not in known:
            return LasViewerRecentSessionBookmarkResult(False, session_key=key, reason="missing_recent_session")
        bookmarks = self._load_bookmarks()
        if key in bookmarks:
            return LasViewerRecentSessionBookmarkResult(False, session_key=key, label=str(bookmarks[key].get("label", "")), reason="already_bookmarked")
        bookmarks[key] = {
            "label": str(removed.get("label", "")),
            "folder": str(removed.get("folder", "")),
            "position": int(removed.get("position", len(bookmarks))),
        }
        trash.pop(key, None)
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            bookmarks=bookmarks,
            bookmark_trash=trash,
            bookmark_trash_journal=self._append_bookmark_trash_event("restored", key, str(removed.get("label", ""))),
        )
        return LasViewerRecentSessionBookmarkResult(True, key, str(removed.get("label", "")), "restored")


    def bookmark_trash_journal(self, *, limit: int = 100) -> tuple[LasViewerRecentSessionBookmarkTrashEvent, ...]:
        """Return newest bookmark trash audit events first."""
        if int(limit) < 1:
            raise ValueError("limit must be >= 1")
        events = self._load_bookmark_trash_journal()
        events.sort(key=lambda item: (-item.occurred_at_ns, item.action, item.session_key))
        return tuple(events[: int(limit)])

    def query_bookmark_trash_journal(
        self,
        *,
        action: str = "",
        session_key: str = "",
        query: str = "",
        occurred_from_ns: int = 0,
        occurred_to_ns: int | None = None,
        limit: int = 100,
    ) -> tuple[LasViewerRecentSessionBookmarkTrashEvent, ...]:
        """Filter bookmark trash audit events for diagnostics and Workbench views."""
        if int(limit) < 1:
            raise ValueError("limit must be >= 1")
        normalized_action = str(action or "").strip()
        if normalized_action and normalized_action not in {"removed", "restored", "purged", "expired"}:
            raise ValueError("unsupported bookmark trash journal action")
        normalized_key = str(session_key or "").strip()
        normalized_query = str(query or "").strip().casefold()
        start_ns = max(0, int(occurred_from_ns))
        stop_ns = None if occurred_to_ns is None else max(0, int(occurred_to_ns))
        if stop_ns is not None and stop_ns < start_ns:
            raise ValueError("occurred_to_ns must be >= occurred_from_ns")

        result: list[LasViewerRecentSessionBookmarkTrashEvent] = []
        for event in self.bookmark_trash_journal(limit=200):
            if normalized_action and event.action != normalized_action:
                continue
            if normalized_key and event.session_key != normalized_key:
                continue
            if event.occurred_at_ns < start_ns:
                continue
            if stop_ns is not None and event.occurred_at_ns > stop_ns:
                continue
            if normalized_query:
                searchable = " ".join((event.action, event.session_key, event.label, event.reason)).casefold()
                if normalized_query not in searchable:
                    continue
            result.append(event)
        return tuple(result[: int(limit)])

    def export_bookmark_trash_journal(
        self,
        path: str | Path,
        *,
        signer_id: str = "",
        signing_key: str | bytes | None = None,
        key_id: str = "",
        **filters: object,
    ) -> dict[str, object]:
        """Atomically export a filtered bookmark trash audit journal as portable JSON."""
        destination = Path(path)
        events = self.query_bookmark_trash_journal(**filters)
        payload: dict[str, object] = {
            "schema": "las.viewer.recent-session-bookmark-trash-journal-export",
            "version": "1.0",
            "exported_at_ns": time.time_ns(),
            "event_count": len(events),
            "events": [event.to_dict() for event in events],
            "renderer_neutral": True,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload["sha256"] = sha256(encoded).hexdigest()
        normalized_signer = str(signer_id or "").strip()
        if signing_key is not None:
            if not normalized_signer:
                raise ValueError("signer_id is required when signing_key is provided")
            key_bytes = signing_key.encode("utf-8") if isinstance(signing_key, str) else bytes(signing_key)
            if not key_bytes:
                raise ValueError("signing_key must not be empty")
            normalized_key_id = str(key_id or "").strip()
            payload["signature"] = {
                "algorithm": "hmac-sha256",
                "signer_id": normalized_signer,
                "key_id": normalized_key_id,
                "value": hmac.new(key_bytes, encoded, sha256).hexdigest(),
            }
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, destination)
        return payload

    @staticmethod
    def _read_bookmark_trash_journal_export(
        path: str | Path,
        *,
        trusted_signers: dict[str, object] | None = None,
        require_signature: bool = False,
        revoked_key_ids: set[str] | frozenset[str] | None = None,
    ) -> list[LasViewerRecentSessionBookmarkTrashEvent]:
        """Validate and decode one portable bookmark trash journal export."""
        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid bookmark trash journal export") from exc
        if not isinstance(payload, dict):
            raise ValueError("invalid bookmark trash journal export")
        if payload.get("schema") != "las.viewer.recent-session-bookmark-trash-journal-export":
            raise ValueError("unsupported bookmark trash journal schema")
        if str(payload.get("version", "")) != "1.0":
            raise ValueError("unsupported bookmark trash journal version")

        expected_sha = str(payload.get("sha256", "")).strip().lower()
        unsigned = dict(payload)
        unsigned.pop("sha256", None)
        signature = unsigned.pop("signature", None)
        encoded = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(expected_sha) != 64 or not hmac.compare_digest(expected_sha, sha256(encoded).hexdigest()):
            raise ValueError("bookmark trash journal integrity check failed")

        if signature is None:
            if require_signature:
                raise ValueError("bookmark trash journal signature is required")
        else:
            if not isinstance(signature, dict) or signature.get("algorithm") != "hmac-sha256":
                raise ValueError("unsupported bookmark trash journal signature")
            signer = str(signature.get("signer_id", "")).strip()
            key_id = str(signature.get("key_id", "")).strip()
            provided = str(signature.get("value", "")).strip().lower()
            trusted = trusted_signers or {}
            if signer not in trusted:
                raise ValueError("untrusted bookmark trash journal signer")
            if key_id and key_id in (revoked_key_ids or set()):
                raise ValueError("revoked bookmark trash journal signing key")
            signer_keys = trusted[signer]
            key_policy: object
            if isinstance(signer_keys, dict) and "key" not in signer_keys:
                if not key_id:
                    raise ValueError("bookmark trash journal key_id is required for rotated keyrings")
                if key_id not in signer_keys:
                    raise ValueError("untrusted bookmark trash journal signing key")
                key_policy = signer_keys[key_id]
            else:
                key_policy = signer_keys

            if isinstance(key_policy, dict):
                if bool(key_policy.get("disabled", False)):
                    raise ValueError("disabled bookmark trash journal signing key")
                if "key" not in key_policy:
                    raise ValueError("trusted bookmark trash journal key policy requires key")
                key = key_policy["key"]
                try:
                    not_before_ns = max(0, int(key_policy.get("not_before_ns", 0)))
                    expires_at_raw = key_policy.get("expires_at_ns")
                    expires_at_ns = None if expires_at_raw is None else max(0, int(expires_at_raw))
                    exported_at_ns = max(0, int(payload.get("exported_at_ns", 0)))
                except (TypeError, ValueError) as exc:
                    raise ValueError("invalid bookmark trash journal key validity policy") from exc
                if expires_at_ns is not None and expires_at_ns < not_before_ns:
                    raise ValueError("invalid bookmark trash journal key validity window")
                if exported_at_ns < not_before_ns:
                    raise ValueError("bookmark trash journal signing key was not active")
                if expires_at_ns is not None and exported_at_ns > expires_at_ns:
                    raise ValueError("expired bookmark trash journal signing key")
            else:
                key = key_policy

            key_bytes = key.encode("utf-8") if isinstance(key, str) else bytes(key)
            if not key_bytes:
                raise ValueError("trusted bookmark trash journal signing key must not be empty")
            expected = hmac.new(key_bytes, encoded, sha256).hexdigest()
            if len(provided) != 64 or not hmac.compare_digest(provided, expected):
                raise ValueError("bookmark trash journal signature verification failed")

        raw_events = payload.get("events", [])
        if not isinstance(raw_events, list) or int(payload.get("event_count", -1)) != len(raw_events):
            raise ValueError("bookmark trash journal event count mismatch")

        result: list[LasViewerRecentSessionBookmarkTrashEvent] = []
        for value in raw_events:
            if not isinstance(value, dict):
                raise ValueError("invalid bookmark trash journal event")
            action = str(value.get("action", "")).strip()
            session_key = str(value.get("session_key", "")).strip()
            if action not in {"removed", "restored", "purged", "expired"} or not session_key:
                raise ValueError("invalid bookmark trash journal event")
            try:
                occurred_at_ns = max(0, int(value.get("occurred_at_ns", 0)))
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid bookmark trash journal timestamp") from exc
            result.append(LasViewerRecentSessionBookmarkTrashEvent(
                action=action,
                session_key=session_key,
                label=str(value.get("label", "")),
                occurred_at_ns=occurred_at_ns,
                reason=str(value.get("reason", "")),
            ))
        return result

    def merge_bookmark_trash_journals(
        self,
        paths: list[str | Path] | tuple[str | Path, ...],
        *,
        trusted_signers: dict[str, object] | None = None,
        require_signatures: bool = False,
        revoked_key_ids: set[str] | frozenset[str] | None = None,
    ) -> dict[str, object]:
        """Transactionally merge validated exports in deterministic event order."""
        sources = tuple(paths)
        decoded = [self._read_bookmark_trash_journal_export_with_audit(
            path,
            trusted_signers=trusted_signers,
            require_signature=require_signatures,
            revoked_key_ids=revoked_key_ids,
            operation="merge",
        ) for path in sources]
        existing = self._load_bookmark_trash_journal()
        seen = {(e.action, e.session_key, e.label, e.occurred_at_ns, e.reason) for e in existing}
        added = 0
        skipped = 0
        for event in (item for batch in decoded for item in batch):
            identity = (event.action, event.session_key, event.label, event.occurred_at_ns, event.reason)
            if identity in seen:
                skipped += 1
                continue
            existing.append(event)
            seen.add(identity)
            added += 1
        existing.sort(key=lambda e: (e.occurred_at_ns, e.action, e.session_key, e.label, e.reason))
        existing = existing[-200:]
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            bookmark_trash_journal=existing,
        )
        return {
            "schema": "las.viewer.recent-session-bookmark-trash-journal-merge-result",
            "version": "1.0",
            "source_count": len(sources),
            "imported": added,
            "skipped": skipped,
            "stored": len(existing),
            "renderer_neutral": True,
        }

    def audit_journal_signature_events(
        self, *, limit: int = 100, accepted: bool | None = None
    ) -> tuple[LasViewerAuditJournalSignatureEvent, ...]:
        """Return newest signature verification audit records first."""
        if int(limit) < 1:
            raise ValueError("limit must be >= 1")
        events = self._load_audit_journal_signature_events()
        if accepted is not None:
            events = [event for event in events if event.accepted is bool(accepted)]
        events.sort(key=lambda event: (-event.occurred_at_ns, event.operation, event.source))
        return tuple(events[: int(limit)])

    def audit_journal_signature_report(
        self,
        *,
        limit: int = 200,
        operation: str = "",
        signer_id: str = "",
    ) -> dict[str, object]:
        """Return a renderer-neutral aggregate report for signature verification audit events."""
        if int(limit) < 1:
            raise ValueError("limit must be >= 1")
        normalized_operation = str(operation or "").strip()
        normalized_signer = str(signer_id or "").strip()
        events = list(self.audit_journal_signature_events(limit=int(limit)))
        if normalized_operation:
            events = [event for event in events if event.operation == normalized_operation]
        if normalized_signer:
            events = [event for event in events if event.signer_id == normalized_signer]

        accepted = sum(1 for event in events if event.accepted)
        rejected = len(events) - accepted
        by_operation: dict[str, dict[str, int]] = {}
        by_signer: dict[str, dict[str, int]] = {}
        rejection_reasons: dict[str, int] = {}

        for event in events:
            operation_key = event.operation or "unknown"
            signer_key = event.signer_id or "unsigned"
            operation_bucket = by_operation.setdefault(operation_key, {"accepted": 0, "rejected": 0})
            signer_bucket = by_signer.setdefault(signer_key, {"accepted": 0, "rejected": 0})
            outcome = "accepted" if event.accepted else "rejected"
            operation_bucket[outcome] += 1
            signer_bucket[outcome] += 1
            if not event.accepted:
                reason = event.reason or "unspecified"
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        total = len(events)
        acceptance_rate = 0.0 if total == 0 else accepted / total
        return {
            "schema": "las.viewer.audit-journal-signature-report",
            "version": "1.0",
            "filters": {
                "limit": int(limit),
                "operation": normalized_operation,
                "signer_id": normalized_signer,
            },
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": acceptance_rate,
            "by_operation": {key: by_operation[key] for key in sorted(by_operation)},
            "by_signer": {key: by_signer[key] for key in sorted(by_signer)},
            "rejection_reasons": {key: rejection_reasons[key] for key in sorted(rejection_reasons)},
            "events": [event.to_dict() for event in events],
            "renderer_neutral": True,
        }

    def export_audit_journal_signature_report(
        self,
        path: str | Path,
        *,
        format: str | None = None,
        limit: int = 200,
        operation: str = "",
        signer_id: str = "",
    ) -> dict[str, object]:
        """Atomically export a verification report as integrity-protected JSON or CSV."""
        destination = Path(path)
        export_format = str(format or destination.suffix.lstrip(".") or "json").strip().lower()
        if export_format not in {"json", "csv"}:
            raise ValueError("format must be json or csv")
        report = self.audit_journal_signature_report(
            limit=limit, operation=operation, signer_id=signer_id
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        exported_at_ns = time.time_ns()

        if export_format == "json":
            unsigned = {
                "schema": "las.viewer.audit-journal-signature-report-export",
                "version": "1.0",
                "format": "json",
                "exported_at_ns": exported_at_ns,
                "report": report,
                "renderer_neutral": True,
            }
            encoded = json.dumps(
                unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            payload = dict(unsigned)
            payload["sha256"] = sha256(encoded).hexdigest()
            text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        else:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(
                buffer,
                fieldnames=(
                    "occurred_at_ns", "operation", "source", "signer_id",
                    "key_id", "accepted", "reason",
                ),
                lineterminator="\n",
            )
            writer.writeheader()
            for event in report["events"]:
                writer.writerow({
                    "occurred_at_ns": event.get("occurred_at_ns", 0),
                    "operation": event.get("operation", ""),
                    "source": event.get("source", ""),
                    "signer_id": event.get("signer_id", ""),
                    "key_id": event.get("key_id", ""),
                    "accepted": str(bool(event.get("accepted", False))).lower(),
                    "reason": event.get("reason", ""),
                })
            body = buffer.getvalue()
            digest = sha256(body.encode("utf-8")).hexdigest()
            metadata = {
                "schema": "las.viewer.audit-journal-signature-report-export",
                "version": "1.0",
                "format": "csv",
                "exported_at_ns": exported_at_ns,
                "event_count": len(report["events"]),
                "sha256": digest,
            }
            text = "# " + json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" + body
            payload = {**metadata, "report": report}

        temporary: Path | None = None
        try:
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=destination.parent, delete=False, newline=""
            ) as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            os.replace(temporary, destination)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink(missing_ok=True)
        return payload

    @staticmethod
    def verify_audit_journal_signature_report_export(path: str | Path) -> dict[str, object]:
        """Verify report export structure and SHA-256 integrity without importing it."""
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError("invalid signature verification report export") from exc

        if text.startswith("# "):
            first, separator, body = text.partition("\n")
            if not separator:
                raise ValueError("invalid signature verification CSV export")
            try:
                metadata = json.loads(first[2:])
            except json.JSONDecodeError as exc:
                raise ValueError("invalid signature verification CSV metadata") from exc
            if not isinstance(metadata, dict) or metadata.get("format") != "csv":
                raise ValueError("invalid signature verification CSV metadata")
            digest = sha256(body.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(str(metadata.get("sha256", "")).lower(), digest):
                raise ValueError("signature verification report integrity check failed")
            rows = list(csv.DictReader(io.StringIO(body)))
            if int(metadata.get("event_count", -1)) != len(rows):
                raise ValueError("signature verification report event count mismatch")
            return {
                "schema": metadata.get("schema"),
                "version": metadata.get("version"),
                "format": "csv",
                "event_count": len(rows),
                "sha256": digest,
                "valid": True,
            }

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid signature verification JSON export") from exc
        if not isinstance(payload, dict) or payload.get("format") != "json":
            raise ValueError("invalid signature verification JSON export")
        expected = str(payload.get("sha256", "")).lower()
        unsigned = dict(payload)
        unsigned.pop("sha256", None)
        encoded = json.dumps(
            unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest = sha256(encoded).hexdigest()
        if len(expected) != 64 or not hmac.compare_digest(expected, digest):
            raise ValueError("signature verification report integrity check failed")
        report = payload.get("report")
        if not isinstance(report, dict) or report.get("schema") != "las.viewer.audit-journal-signature-report":
            raise ValueError("invalid signature verification report payload")
        events = report.get("events")
        if not isinstance(events, list) or int(report.get("total", -1)) != len(events):
            raise ValueError("signature verification report event count mismatch")
        return {
            "schema": payload.get("schema"),
            "version": payload.get("version"),
            "format": "json",
            "event_count": len(events),
            "sha256": digest,
            "valid": True,
        }

    @classmethod
    def read_audit_journal_signature_report_export(
        cls, path: str | Path
    ) -> tuple[LasViewerAuditJournalSignatureEvent, ...]:
        """Read and validate an integrity-protected verification report export."""
        source = Path(path)
        verified = cls.verify_audit_journal_signature_report_export(source)
        text = source.read_text(encoding="utf-8")
        raw_events: list[dict[str, object]] = []

        if verified["format"] == "json":
            payload = json.loads(text)
            report = payload.get("report", {})
            events = report.get("events", []) if isinstance(report, dict) else []
            if not isinstance(events, list):
                raise ValueError("invalid signature verification report events")
            raw_events = [event for event in events if isinstance(event, dict)]
            if len(raw_events) != len(events):
                raise ValueError("invalid signature verification report event")
        else:
            _, separator, body = text.partition("\n")
            if not separator:
                raise ValueError("invalid signature verification CSV export")
            try:
                raw_events = [dict(row) for row in csv.DictReader(io.StringIO(body))]
            except (csv.Error, TypeError) as exc:
                raise ValueError("invalid signature verification report events") from exc

        decoded: list[LasViewerAuditJournalSignatureEvent] = []
        for value in raw_events:
            try:
                occurred_at_ns = max(0, int(value.get("occurred_at_ns", 0)))
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid signature verification report timestamp") from exc
            accepted_value = value.get("accepted", False)
            if isinstance(accepted_value, str):
                normalized = accepted_value.strip().lower()
                if normalized not in {"true", "false"}:
                    raise ValueError("invalid signature verification report outcome")
                accepted = normalized == "true"
            elif isinstance(accepted_value, bool):
                accepted = accepted_value
            else:
                raise ValueError("invalid signature verification report outcome")
            decoded.append(LasViewerAuditJournalSignatureEvent(
                source=str(value.get("source", "")),
                operation=str(value.get("operation", "")),
                accepted=accepted,
                signer_id=str(value.get("signer_id", "")),
                key_id=str(value.get("key_id", "")),
                reason=str(value.get("reason", "")),
                occurred_at_ns=occurred_at_ns,
            ))

        if len(decoded) != int(verified["event_count"]):
            raise ValueError("signature verification report event count mismatch")
        return tuple(decoded)

    @classmethod
    def compare_audit_journal_signature_report_exports(
        cls,
        baseline_path: str | Path,
        candidate_path: str | Path,
    ) -> dict[str, object]:
        """Compare two validated verification report exports without importing them.

        Events are matched by their complete stable identity, so duplicate records are
        handled deterministically and no repository state is modified.
        """
        baseline = cls.read_audit_journal_signature_report_export(baseline_path)
        candidate = cls.read_audit_journal_signature_report_export(candidate_path)

        def identity(event: LasViewerAuditJournalSignatureEvent) -> tuple[object, ...]:
            return (
                event.source,
                event.operation,
                event.accepted,
                event.signer_id,
                event.key_id,
                event.reason,
                event.occurred_at_ns,
            )

        baseline_map = {identity(event): event for event in baseline}
        candidate_map = {identity(event): event for event in candidate}
        baseline_keys = set(baseline_map)
        candidate_keys = set(candidate_map)

        added = [candidate_map[key] for key in sorted(candidate_keys - baseline_keys)]
        removed = [baseline_map[key] for key in sorted(baseline_keys - candidate_keys)]
        unchanged = baseline_keys & candidate_keys

        baseline_accepted = sum(1 for event in baseline if event.accepted)
        candidate_accepted = sum(1 for event in candidate if event.accepted)
        baseline_rejected = len(baseline) - baseline_accepted
        candidate_rejected = len(candidate) - candidate_accepted

        return {
            "schema": "las.viewer.audit-journal-signature-report-comparison",
            "version": "1.0",
            "baseline": {
                "path": str(Path(baseline_path)),
                "total": len(baseline),
                "accepted": baseline_accepted,
                "rejected": baseline_rejected,
            },
            "candidate": {
                "path": str(Path(candidate_path)),
                "total": len(candidate),
                "accepted": candidate_accepted,
                "rejected": candidate_rejected,
            },
            "delta": {
                "total": len(candidate) - len(baseline),
                "accepted": candidate_accepted - baseline_accepted,
                "rejected": candidate_rejected - baseline_rejected,
            },
            "added_count": len(added),
            "removed_count": len(removed),
            "unchanged_count": len(unchanged),
            "changed": bool(added or removed),
            "added": [event.to_dict() for event in added],
            "removed": [event.to_dict() for event in removed],
            "renderer_neutral": True,
        }

    def import_audit_journal_signature_reports(
        self, paths: list[str | Path] | tuple[str | Path, ...]
    ) -> dict[str, object]:
        """Transactionally import and merge validated verification report exports."""
        sources = tuple(paths)
        decoded = [self.read_audit_journal_signature_report_export(path) for path in sources]
        existing = self._load_audit_journal_signature_events()
        identity = lambda event: (
            event.source, event.operation, event.accepted, event.signer_id,
            event.key_id, event.reason, event.occurred_at_ns,
        )
        seen = {identity(event) for event in existing}
        imported = 0
        skipped = 0
        for event in (event for batch in decoded for event in batch):
            key = identity(event)
            if key in seen:
                skipped += 1
                continue
            existing.append(event)
            seen.add(key)
            imported += 1
        existing.sort(key=lambda event: (
            event.occurred_at_ns, event.operation, event.source,
            event.signer_id, event.key_id, event.reason, event.accepted,
        ))
        existing = existing[-200:]
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            audit_journal_signature_events=existing,
        )
        return {
            "schema": "las.viewer.audit-journal-signature-report-import-result",
            "version": "1.0",
            "source_count": len(sources),
            "imported": imported,
            "skipped": skipped,
            "stored": len(existing),
            "renderer_neutral": True,
        }

    def verify_bookmark_trash_journal_export(
        self,
        path: str | Path,
        *,
        trusted_signers: dict[str, object] | None = None,
        require_signature: bool = False,
        revoked_key_ids: set[str] | frozenset[str] | None = None,
        operation: str = "verify",
    ) -> dict[str, object]:
        """Verify one journal export and persist a structured audit result."""
        source = Path(path)
        signer_id = ""
        key_id = ""
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("signature"), dict):
                signature = raw["signature"]
                signer_id = str(signature.get("signer_id", "")).strip()
                key_id = str(signature.get("key_id", "")).strip()
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass

        accepted = False
        reason = ""
        event_count = 0
        try:
            events = self._read_bookmark_trash_journal_export(
                source,
                trusted_signers=trusted_signers,
                require_signature=require_signature,
                revoked_key_ids=revoked_key_ids,
            )
            accepted = True
            event_count = len(events)
        except ValueError as exc:
            reason = str(exc)

        audit = LasViewerAuditJournalSignatureEvent(
            source=source.name,
            operation=str(operation or "verify").strip() or "verify",
            accepted=accepted,
            signer_id=signer_id,
            key_id=key_id,
            reason=reason,
            occurred_at_ns=time.time_ns(),
        )
        records = self._load_audit_journal_signature_events()
        records.append(audit)
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            audit_journal_signature_events=records[-200:],
        )
        return {
            "schema": "las.viewer.audit-journal-signature-verification",
            "version": "1.0",
            "accepted": accepted,
            "source": source.name,
            "operation": audit.operation,
            "signer_id": signer_id,
            "key_id": key_id,
            "event_count": event_count,
            "reason": reason,
            "renderer_neutral": True,
        }

    def _read_bookmark_trash_journal_export_with_audit(
        self,
        path: str | Path,
        *,
        trusted_signers: dict[str, object] | None,
        require_signature: bool,
        revoked_key_ids: set[str] | frozenset[str] | None,
        operation: str,
    ) -> list[LasViewerRecentSessionBookmarkTrashEvent]:
        result = self.verify_bookmark_trash_journal_export(
            path,
            trusted_signers=trusted_signers,
            require_signature=require_signature,
            revoked_key_ids=revoked_key_ids,
            operation=operation,
        )
        if not result["accepted"]:
            raise ValueError(str(result["reason"]))
        return self._read_bookmark_trash_journal_export(
            path,
            trusted_signers=trusted_signers,
            require_signature=require_signature,
            revoked_key_ids=revoked_key_ids,
        )

    def import_bookmark_trash_journal(
        self,
        path: str | Path,
        *,
        mode: str = "append",
        trusted_signers: dict[str, object] | None = None,
        require_signature: bool = False,
        revoked_key_ids: set[str] | frozenset[str] | None = None,
    ) -> dict[str, object]:
        """Restore an exported audit journal after validating schema and SHA-256 integrity."""
        normalized_mode = str(mode or "append").strip().lower()
        if normalized_mode not in {"append", "replace"}:
            raise ValueError("mode must be one of: append, replace")

        imported = self._read_bookmark_trash_journal_export_with_audit(
            path,
            trusted_signers=trusted_signers,
            require_signature=require_signature,
            revoked_key_ids=revoked_key_ids,
            operation="import",
        )

        existing = [] if normalized_mode == "replace" else self._load_bookmark_trash_journal()
        seen = {(event.action, event.session_key, event.label, event.occurred_at_ns, event.reason) for event in existing}
        added = 0
        for event in imported:
            identity = (event.action, event.session_key, event.label, event.occurred_at_ns, event.reason)
            if identity in seen:
                continue
            existing.append(event)
            seen.add(identity)
            added += 1
        existing = existing[-200:]
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            bookmark_trash_journal=existing,
        )
        return {
            "schema": "las.viewer.recent-session-bookmark-trash-journal-import-result",
            "version": "1.0",
            "mode": normalized_mode,
            "imported": added,
            "skipped": len(imported) - added,
            "stored": len(existing),
            "renderer_neutral": True,
        }

    def clear_bookmark_trash_journal(self) -> int:
        """Clear persisted trash audit events without changing trash contents."""
        removed = len(self._load_bookmark_trash_journal())
        if removed:
            self._save_preferences(
                pinned_keys=self._load_pinned_keys(),
                collapsed_groups=self._load_collapsed_groups(),
                navigation_state=self.navigation_state(),
                navigation_history=self.navigation_history(),
                bookmark_trash_journal=[],
            )
        return removed

    def bookmark_trash_retention(self) -> LasViewerRecentSessionBookmarkTrashRetention:
        """Load the persisted automatic trash cleanup policy."""
        payload = self._load_preferences()
        raw = payload.get("bookmark_trash_retention", {})
        if not isinstance(raw, dict):
            raw = {}
        try:
            retention_days = float(raw.get("retention_days", 30.0))
        except (TypeError, ValueError):
            retention_days = 30.0
        if retention_days < 0 or retention_days != retention_days or retention_days == float("inf"):
            retention_days = 30.0
        try:
            last_cleanup_ns = max(0, int(raw.get("last_cleanup_ns", 0)))
        except (TypeError, ValueError):
            last_cleanup_ns = 0
        return LasViewerRecentSessionBookmarkTrashRetention(
            enabled=bool(raw.get("enabled", False)),
            retention_days=retention_days,
            last_cleanup_ns=last_cleanup_ns,
        )

    def configure_bookmark_trash_retention(
        self,
        retention_days: float | None,
    ) -> LasViewerRecentSessionBookmarkTrashRetention:
        """Enable automatic cleanup, or disable it when ``retention_days`` is None."""
        if retention_days is None:
            current = self.bookmark_trash_retention()
            policy = LasViewerRecentSessionBookmarkTrashRetention(
                enabled=False,
                retention_days=current.retention_days,
                last_cleanup_ns=current.last_cleanup_ns,
            )
        else:
            try:
                days = float(retention_days)
            except (TypeError, ValueError) as exc:
                raise ValueError("retention_days must be a finite non-negative number") from exc
            if days < 0 or days != days or days == float("inf"):
                raise ValueError("retention_days must be a finite non-negative number")
            current = self.bookmark_trash_retention()
            policy = LasViewerRecentSessionBookmarkTrashRetention(
                enabled=True,
                retention_days=days,
                last_cleanup_ns=current.last_cleanup_ns,
            )
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            bookmark_trash_retention=policy,
        )
        return policy

    def synchronize_bookmark_trash(self, *, now_ns: int | None = None) -> int:
        """Apply the persisted retention policy after startup or repository refresh."""
        policy = self.bookmark_trash_retention()
        if not policy.enabled:
            return 0
        current_ns = time.time_ns() if now_ns is None else int(now_ns)
        if current_ns < 0:
            raise ValueError("now_ns must be non-negative")
        cutoff_ns = current_ns - int(policy.retention_days * 86_400_000_000_000)
        trash = self._load_bookmark_trash()
        updated = {
            key: value
            for key, value in trash.items()
            if int(value.get("deleted_at_ns", 0)) <= 0
            or int(value.get("deleted_at_ns", 0)) > cutoff_ns
        }
        removed_count = len(trash) - len(updated)
        next_policy = LasViewerRecentSessionBookmarkTrashRetention(
            enabled=True,
            retention_days=policy.retention_days,
            last_cleanup_ns=current_ns,
        )
        self._save_preferences(
            pinned_keys=self._load_pinned_keys(),
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
            bookmark_trash=updated,
            bookmark_trash_retention=next_policy,
            bookmark_trash_journal=(self._append_bookmark_trash_event("expired", "", reason=f"removed:{removed_count}", occurred_at_ns=current_ns) if removed_count else self._load_bookmark_trash_journal()),
        )
        return removed_count

    def purge_expired_bookmark_trash(
        self,
        retention_days: float,
        *,
        now_ns: int | None = None,
    ) -> int:
        """Permanently remove trash items older than the retention period.

        Legacy trash entries without ``deleted_at_ns`` are preserved because their
        age cannot be determined safely.
        """
        try:
            days = float(retention_days)
        except (TypeError, ValueError) as exc:
            raise ValueError("retention_days must be a non-negative number") from exc
        if days < 0 or days != days or days == float("inf"):
            raise ValueError("retention_days must be a finite non-negative number")
        current_ns = time.time_ns() if now_ns is None else int(now_ns)
        if current_ns < 0:
            raise ValueError("now_ns must be non-negative")
        cutoff_ns = current_ns - int(days * 86_400_000_000_000)
        trash = self._load_bookmark_trash()
        updated = {
            key: value
            for key, value in trash.items()
            if int(value.get("deleted_at_ns", 0)) <= 0
            or int(value.get("deleted_at_ns", 0)) > cutoff_ns
        }
        removed_count = len(trash) - len(updated)
        if removed_count:
            self._save_preferences(
                pinned_keys=self._load_pinned_keys(),
                collapsed_groups=self._load_collapsed_groups(),
                navigation_state=self.navigation_state(),
                navigation_history=self.navigation_history(),
                bookmark_trash=updated,
                bookmark_trash_journal=self._append_bookmark_trash_event("expired", "", reason=f"removed:{removed_count}", occurred_at_ns=current_ns),
            )
        return removed_count

    def purge_bookmark_trash(self, session_key: str | None = None) -> int:
        """Permanently remove one trash item or clear the entire bookmark trash."""
        trash = self._load_bookmark_trash()
        if session_key is None:
            removed_count = len(trash)
            updated: dict[str, dict[str, object]] = {}
        else:
            key = str(session_key or "").strip()
            if not key or key not in trash:
                return 0
            updated = dict(trash)
            updated.pop(key, None)
            removed_count = 1
        if removed_count:
            self._save_preferences(
                pinned_keys=self._load_pinned_keys(),
                collapsed_groups=self._load_collapsed_groups(),
                navigation_state=self.navigation_state(),
                navigation_history=self.navigation_history(),
                bookmark_trash=updated,
                bookmark_trash_journal=self._append_bookmark_trash_event(
                    "purged",
                    "" if session_key is None else str(session_key).strip(),
                    reason=f"removed:{removed_count}",
                ),
            )
        return removed_count

    def focus_bookmark(
        self,
        session_key: str,
        *,
        group_by: str = "project",
        page_size: int = 10,
    ) -> LasViewerRecentSessionNavigationTarget:
        """Resolve and persist navigation to a bookmarked recent session."""
        if str(session_key or "").strip() not in self._load_bookmarks():
            return LasViewerRecentSessionNavigationTarget(
                found=False,
                session_key=str(session_key or "").strip(),
                group_by=str(group_by or "project").strip().lower(),
                reason="missing_bookmark",
            )
        return self.locate_session(
            session_key,
            group_by=group_by,
            page_size=page_size,
            persist=True,
        )

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
                bookmarks = self._load_bookmarks()
                keys.discard(key)
                bookmarks.pop(key, None)
                self._save_preferences(
                    pinned_keys=keys,
                    collapsed_groups=self._load_collapsed_groups(),
                    navigation_state=self.navigation_state(),
                    navigation_history=self.navigation_history(),
                    bookmarks=bookmarks,
                )
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
        query: str = "",
        project_id: str = "",
        las_id: str = "",
        pinned_only: bool = False,
        active_only: bool = False,
        sort_by: str = "modified",
        sort_order: str = "desc",
        pinned_first: bool = True,
    ) -> dict[str, object]:
        items = self.list(
            limit=limit,
            include_invalid=include_invalid,
            active_project_id=active_project_id,
            active_las_id=active_las_id,
            query=query,
            project_id=project_id,
            las_id=las_id,
            pinned_only=pinned_only,
            active_only=active_only,
            sort_by=sort_by,
            sort_order=sort_order,
            pinned_first=pinned_first,
        )
        return {
            "schema": "las.viewer.recent-sessions",
            "version": "1.3",
            "items": [item.to_dict() for item in items],
            "count": len(items),
            "pinned_count": sum(1 for item in items if item.pinned),
            "filters": {
                "query": str(query or "").strip(),
                "project_id": str(project_id or "").strip(),
                "las_id": str(las_id or "").strip(),
                "pinned_only": bool(pinned_only),
                "active_only": bool(active_only),
                "include_invalid": bool(include_invalid),
            },
            "sorting": {
                "sort_by": str(sort_by or "modified").strip().lower(),
                "sort_order": str(sort_order or "desc").strip().lower(),
                "pinned_first": bool(pinned_first),
            },
            "renderer_neutral": True,
        }


    @staticmethod
    def _sort_items(
        items: list[LasViewerRecentSession],
        *,
        sort_by: str,
        sort_order: str,
        pinned_first: bool,
    ) -> list[LasViewerRecentSession]:
        def field_value(item: LasViewerRecentSession):
            if sort_by == "modified":
                return item.modified_ns
            if sort_by == "filename":
                return item.filename.casefold()
            if sort_by == "project":
                return item.project_id.casefold()
            return item.las_id.casefold()

        ordered = sorted(
            items,
            key=lambda item: (field_value(item), item.filename.casefold(), item.session_key),
            reverse=sort_order == "desc",
        )
        if pinned_first:
            ordered = sorted(ordered, key=lambda item: not item.pinned)
        return ordered

    @staticmethod
    def _matches_filters(
        item: LasViewerRecentSession,
        *,
        query: str,
        project_id: str,
        las_id: str,
        pinned_only: bool,
        active_only: bool,
    ) -> bool:
        if project_id and item.project_id != project_id:
            return False
        if las_id and item.las_id != las_id:
            return False
        if pinned_only and not item.pinned:
            return False
        if active_only and not item.active:
            return False
        if query:
            searchable = "\0".join((item.filename, item.project_id, item.las_id)).casefold()
            if query not in searchable:
                return False
        return True

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

    def _load_preferences(self) -> dict[str, object]:
        if not self._metadata_path.is_file():
            return {}
        try:
            payload = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        if payload.get("schema") != "las.viewer.recent-session-preferences":
            return {}
        return payload

    def _load_pinned_keys(self) -> set[str]:
        payload = self._load_preferences()
        raw = payload.get("pinned_session_keys", [])
        if not isinstance(raw, list):
            return set()
        return {str(value).strip() for value in raw if str(value).strip()}


    def _load_bookmarks(self) -> dict[str, dict[str, object]]:
        payload = self._load_preferences()
        raw = payload.get("bookmarks", {})
        if not isinstance(raw, dict):
            return {}
        result: dict[str, dict[str, object]] = {}
        for index, (key, value) in enumerate(raw.items()):
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            if isinstance(value, str):
                label = value.strip()
                if label:
                    result[normalized_key] = {"label": label, "folder": "", "position": index}
                continue
            if not isinstance(value, dict):
                continue
            label = str(value.get("label", "")).strip()
            if not label:
                continue
            try:
                position = max(0, int(value.get("position", index)))
            except (TypeError, ValueError):
                position = index
            result[normalized_key] = {
                "label": label,
                "folder": str(value.get("folder", "") or "").strip(),
                "position": position,
            }
        return result

    def _load_bookmark_trash(self) -> dict[str, dict[str, object]]:
        payload = self._load_preferences()
        raw = payload.get("bookmark_trash", {})
        if not isinstance(raw, dict):
            return {}
        result: dict[str, dict[str, object]] = {}
        for index, (key, value) in enumerate(raw.items()):
            normalized_key = str(key).strip()
            if not normalized_key or not isinstance(value, dict):
                continue
            label = str(value.get("label", "")).strip()
            if not label:
                continue
            try:
                position = max(0, int(value.get("position", 0)))
                deletion_order = max(0, int(value.get("deletion_order", index + 1)))
                deleted_at_ns = max(0, int(value.get("deleted_at_ns", 0)))
            except (TypeError, ValueError):
                continue
            result[normalized_key] = {
                "label": label,
                "folder": str(value.get("folder", "") or "").strip(),
                "position": position,
                "deletion_order": deletion_order,
                "deleted_at_ns": deleted_at_ns,
            }
        return result

    def _load_bookmark_trash_journal(self) -> list[LasViewerRecentSessionBookmarkTrashEvent]:
        payload = self._load_preferences()
        raw = payload.get("bookmark_trash_journal", [])
        if not isinstance(raw, list):
            return []
        result: list[LasViewerRecentSessionBookmarkTrashEvent] = []
        for value in raw:
            if not isinstance(value, dict):
                continue
            action = str(value.get("action", "")).strip()
            session_key = str(value.get("session_key", "")).strip()
            if action not in {"removed", "restored", "purged", "expired"}:
                continue
            try:
                occurred_at_ns = max(0, int(value.get("occurred_at_ns", 0)))
            except (TypeError, ValueError):
                continue
            result.append(LasViewerRecentSessionBookmarkTrashEvent(
                action=action, session_key=session_key,
                label=str(value.get("label", "")),
                occurred_at_ns=occurred_at_ns,
                reason=str(value.get("reason", "")),
            ))
        return result

    def _append_bookmark_trash_event(
        self, action: str, session_key: str, label: str = "", *, reason: str = "", occurred_at_ns: int | None = None
    ) -> list[LasViewerRecentSessionBookmarkTrashEvent]:
        events = self._load_bookmark_trash_journal()
        events.append(LasViewerRecentSessionBookmarkTrashEvent(
            action=action, session_key=session_key, label=label,
            occurred_at_ns=time.time_ns() if occurred_at_ns is None else max(0, int(occurred_at_ns)),
            reason=reason,
        ))
        return events[-200:]

    def _load_audit_journal_signature_events(self) -> list[LasViewerAuditJournalSignatureEvent]:
        payload = self._load_preferences()
        raw = payload.get("audit_journal_signature_events", [])
        if not isinstance(raw, list):
            return []
        result: list[LasViewerAuditJournalSignatureEvent] = []
        for value in raw:
            if not isinstance(value, dict):
                continue
            try:
                occurred_at_ns = max(0, int(value.get("occurred_at_ns", 0)))
            except (TypeError, ValueError):
                continue
            result.append(LasViewerAuditJournalSignatureEvent(
                source=str(value.get("source", "")),
                operation=str(value.get("operation", "verify")),
                accepted=bool(value.get("accepted", False)),
                signer_id=str(value.get("signer_id", "")),
                key_id=str(value.get("key_id", "")),
                reason=str(value.get("reason", "")),
                occurred_at_ns=occurred_at_ns,
            ))
        return result

    def _load_collapsed_groups(self) -> set[str]:
        payload = self._load_preferences()
        raw = payload.get("collapsed_groups", [])
        if not isinstance(raw, list):
            return set()
        return {str(value).strip() for value in raw if str(value).strip()}

    def _save_pinned_keys(self, keys: set[str]) -> None:
        self._save_preferences(
            pinned_keys=keys,
            collapsed_groups=self._load_collapsed_groups(),
            navigation_state=self.navigation_state(),
            navigation_history=self.navigation_history(),
        )

    def _save_preferences(
        self,
        *,
        pinned_keys: set[str],
        collapsed_groups: set[str],
        navigation_state: LasViewerRecentSessionNavigationState | None = None,
        navigation_history: LasViewerRecentSessionNavigationHistory | None = None,
        bookmarks: dict[str, dict[str, object]] | None = None,
        bookmark_trash: dict[str, dict[str, object]] | None = None,
        bookmark_trash_retention: LasViewerRecentSessionBookmarkTrashRetention | None = None,
        bookmark_trash_journal: list[LasViewerRecentSessionBookmarkTrashEvent] | None = None,
        audit_journal_signature_events: list[LasViewerAuditJournalSignatureEvent] | None = None,
    ) -> None:
        self.repository.directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "las.viewer.recent-session-preferences",
            "version": "2.0",
            "pinned_session_keys": sorted(pinned_keys),
            "collapsed_groups": sorted(collapsed_groups),
            "navigation_state": (navigation_state or self.navigation_state()).to_dict(),
            "navigation_history": (navigation_history or self.navigation_history()).to_dict(),
            "bookmarks": dict(sorted((bookmarks if bookmarks is not None else self._load_bookmarks()).items())),
            "bookmark_trash": dict(sorted((bookmark_trash if bookmark_trash is not None else self._load_bookmark_trash()).items())),
            "bookmark_trash_retention": (bookmark_trash_retention or self.bookmark_trash_retention()).to_dict(),
            "bookmark_trash_journal": [event.to_dict() for event in (bookmark_trash_journal if bookmark_trash_journal is not None else self._load_bookmark_trash_journal())],
            "audit_journal_signature_events": [event.to_dict() for event in (audit_journal_signature_events if audit_journal_signature_events is not None else self._load_audit_journal_signature_events())],
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

