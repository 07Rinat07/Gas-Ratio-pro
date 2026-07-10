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
    ) -> None:
        self.repository.directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "las.viewer.recent-session-preferences",
            "version": "1.3",
            "pinned_session_keys": sorted(pinned_keys),
            "collapsed_groups": sorted(collapsed_groups),
            "navigation_state": (navigation_state or self.navigation_state()).to_dict(),
            "navigation_history": (navigation_history or self.navigation_history()).to_dict(),
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

