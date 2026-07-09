"""Workspace session manager for Modern UI state restoration.

The workspace reset module clears stale derived data.  This module handles the
opposite workflow: capture the current user workspace, persist a small and safe
session descriptor, and restore it later without coupling the UI to raw
``st.session_state`` keys.

A workspace session intentionally stores only lightweight UI context: active
project/well/LAS/workspace ids, opened files, selected intervals, active report
or plot identifiers, recent exports and window layout.  It must not store large
LAS dataframes, calculation tables, plot payloads or raw interpretation dumps.
Those artifacts are recreated from the project data when the session is opened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any, Iterable, Literal, MutableMapping

from core.application_state import (
    ACTIVE_LAS_ID_KEY,
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
    ApplicationStateController,
)

WORKSPACE_SESSION_SCHEMA = "gas-ratio-pro/workspace-session/v1"

SESSION_OPENED_FILES_KEY = "workspace_session_opened_files"
SESSION_SELECTED_INTERVALS_KEY = "workspace_session_selected_intervals"
SESSION_ACTIVE_REPORT_KEY = "workspace_session_active_report"
SESSION_ACTIVE_PLOT_KEY = "workspace_session_active_plot"
SESSION_USER_PROFILE_KEY = "workspace_session_user_profile"
SESSION_RECENT_EXPORTS_KEY = "workspace_session_recent_exports"
SESSION_WINDOW_LAYOUT_KEY = "workspace_session_window_layout"
SESSION_LAST_RESTORED_KEY = "workspace_session_last_restored"
SESSION_LAST_SAVED_KEY = "workspace_session_last_saved"

RestoreConflictPolicy = Literal["overwrite", "preserve"]

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, Iterable):
        result: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                result.append(text)
        return tuple(result)
    text = str(value or "").strip()
    return (text,) if text else ()


def _dict_copy(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_filename_token(value: str, *, fallback: str = "workspace") -> str:
    token = _SAFE_ID_RE.sub("_", str(value or "").strip()).strip("._-")
    return token or fallback


@dataclass(frozen=True)
class WorkspaceSession:
    """Small, serializable descriptor of the user's current workspace."""

    project_id: str = ""
    well_id: str = ""
    las_id: str = ""
    workspace_id: str = ""
    opened_files: tuple[str, ...] = ()
    selected_intervals: tuple[str, ...] = ()
    active_report: str = ""
    active_plot: str = ""
    user_profile: str = "engineering"
    recent_exports: tuple[str, ...] = ()
    window_layout: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_utc)
    updated_at: str = field(default_factory=_now_utc)
    schema: str = WORKSPACE_SESSION_SCHEMA

    @classmethod
    def from_state(cls, state: MutableMapping[str, Any]) -> "WorkspaceSession":
        """Capture a session from application state.

        Only lightweight keys are read.  Heavy transient data such as dataframes
        and rendered Plotly figures are intentionally ignored.
        """

        return cls(
            project_id=str(state.get(ACTIVE_PROJECT_ID_KEY, "") or ""),
            well_id=str(state.get(ACTIVE_WELL_ID_KEY, "") or ""),
            las_id=str(state.get(ACTIVE_LAS_ID_KEY, "") or ""),
            workspace_id=str(state.get(ACTIVE_WORKSPACE_ID_KEY, "") or ""),
            opened_files=_string_tuple(state.get(SESSION_OPENED_FILES_KEY, ())),
            selected_intervals=_string_tuple(state.get(SESSION_SELECTED_INTERVALS_KEY, ())),
            active_report=str(state.get(SESSION_ACTIVE_REPORT_KEY, "") or ""),
            active_plot=str(state.get(SESSION_ACTIVE_PLOT_KEY, "") or ""),
            user_profile=str(state.get(SESSION_USER_PROFILE_KEY, "engineering") or "engineering"),
            recent_exports=_string_tuple(state.get(SESSION_RECENT_EXPORTS_KEY, ())),
            window_layout=_dict_copy(state.get(SESSION_WINDOW_LAYOUT_KEY, {})),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceSession":
        """Build a session from JSON-compatible data with defensive defaults."""

        return cls(
            project_id=str(data.get("project_id", "") or ""),
            well_id=str(data.get("well_id", "") or ""),
            las_id=str(data.get("las_id", "") or ""),
            workspace_id=str(data.get("workspace_id", "") or ""),
            opened_files=_string_tuple(data.get("opened_files", ())),
            selected_intervals=_string_tuple(data.get("selected_intervals", ())),
            active_report=str(data.get("active_report", "") or ""),
            active_plot=str(data.get("active_plot", "") or ""),
            user_profile=str(data.get("user_profile", "engineering") or "engineering"),
            recent_exports=_string_tuple(data.get("recent_exports", ())),
            window_layout=_dict_copy(data.get("window_layout", {})),
            created_at=str(data.get("created_at", "") or _now_utc()),
            updated_at=str(data.get("updated_at", "") or _now_utc()),
            schema=str(data.get("schema", WORKSPACE_SESSION_SCHEMA) or WORKSPACE_SESSION_SCHEMA),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "project_id": self.project_id,
            "well_id": self.well_id,
            "las_id": self.las_id,
            "workspace_id": self.workspace_id,
            "opened_files": list(self.opened_files),
            "selected_intervals": list(self.selected_intervals),
            "active_report": self.active_report,
            "active_plot": self.active_plot,
            "user_profile": self.user_profile,
            "recent_exports": list(self.recent_exports),
            "window_layout": dict(self.window_layout),
        }

    def session_id(self) -> str:
        """Return a stable readable id for filenames and UI lists."""

        base = "-".join(
            token
            for token in (
                _safe_filename_token(self.project_id, fallback="project"),
                _safe_filename_token(self.well_id, fallback="well"),
                _safe_filename_token(self.workspace_id or self.las_id, fallback="workspace"),
            )
            if token
        )
        return base or "workspace-session"


@dataclass(frozen=True)
class WorkspaceSessionResult:
    """Result returned by save/restore operations."""

    executed: bool
    session: WorkspaceSession
    path: str = ""
    affected_keys: tuple[str, ...] = ()
    message: str = ""


class WorkspaceSessionManager:
    """Capture, persist and restore lightweight workspace sessions."""

    def __init__(self, state: MutableMapping[str, Any], *, sessions_dir: str | Path = "data/sessions") -> None:
        self.state = state
        self.sessions_dir = Path(sessions_dir)
        self.state_controller = ApplicationStateController(state)

    def capture(self) -> WorkspaceSession:
        return WorkspaceSession.from_state(self.state)

    def session_path(self, session: WorkspaceSession | None = None, *, suffix: str = ".json") -> Path:
        current = session or self.capture()
        return self.sessions_dir / f"{current.session_id()}{suffix}"

    def save(self, path: str | Path | None = None) -> WorkspaceSessionResult:
        """Persist the current lightweight session to JSON."""

        session = self.capture()
        target = Path(path) if path is not None else self.session_path(session)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = session.to_dict()
        payload["updated_at"] = _now_utc()
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.state[SESSION_LAST_SAVED_KEY] = str(target)
        return WorkspaceSessionResult(
            executed=True,
            session=WorkspaceSession.from_dict(payload),
            path=str(target),
            affected_keys=(SESSION_LAST_SAVED_KEY,),
            message="Workspace session saved.",
        )

    def load(self, path: str | Path) -> WorkspaceSession:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Workspace session file must contain a JSON object.")
        return WorkspaceSession.from_dict(data)

    def restore(
        self,
        session: WorkspaceSession,
        *,
        conflict_policy: RestoreConflictPolicy = "overwrite",
    ) -> WorkspaceSessionResult:
        """Restore a session into application state.

        ``overwrite`` restores all stored keys.  ``preserve`` only fills empty
        values so the UI can reopen a session without replacing an already
        selected context.
        """

        def should_write(key: str) -> bool:
            return conflict_policy == "overwrite" or not bool(self.state.get(key))

        values: dict[str, Any] = {
            ACTIVE_PROJECT_ID_KEY: session.project_id,
            ACTIVE_WELL_ID_KEY: session.well_id,
            ACTIVE_LAS_ID_KEY: session.las_id,
            ACTIVE_WORKSPACE_ID_KEY: session.workspace_id,
            SESSION_OPENED_FILES_KEY: list(session.opened_files),
            SESSION_SELECTED_INTERVALS_KEY: list(session.selected_intervals),
            SESSION_ACTIVE_REPORT_KEY: session.active_report,
            SESSION_ACTIVE_PLOT_KEY: session.active_plot,
            SESSION_USER_PROFILE_KEY: session.user_profile,
            SESSION_RECENT_EXPORTS_KEY: list(session.recent_exports),
            SESSION_WINDOW_LAYOUT_KEY: dict(session.window_layout),
        }
        affected: list[str] = []
        for key, value in values.items():
            if should_write(key):
                self.state[key] = value
                affected.append(key)
        self.state[SESSION_LAST_RESTORED_KEY] = _now_utc()
        affected.append(SESSION_LAST_RESTORED_KEY)
        self.state_controller._event_bus().publish(
            "workspace.session.restored",
            {
                "project_id": session.project_id,
                "well_id": session.well_id,
                "las_id": session.las_id,
                "workspace_id": session.workspace_id,
                "conflict_policy": conflict_policy,
            },
        )
        return WorkspaceSessionResult(
            executed=True,
            session=session,
            affected_keys=tuple(sorted(set(affected))),
            message="Workspace session restored.",
        )

    def load_and_restore(
        self,
        path: str | Path,
        *,
        conflict_policy: RestoreConflictPolicy = "overwrite",
    ) -> WorkspaceSessionResult:
        session = self.load(path)
        result = self.restore(session, conflict_policy=conflict_policy)
        return WorkspaceSessionResult(
            executed=result.executed,
            session=result.session,
            path=str(path),
            affected_keys=result.affected_keys,
            message=result.message,
        )


def workspace_session_keys() -> tuple[str, ...]:
    """Return UI-owned keys controlled by WorkspaceSessionManager."""

    return (
        SESSION_OPENED_FILES_KEY,
        SESSION_SELECTED_INTERVALS_KEY,
        SESSION_ACTIVE_REPORT_KEY,
        SESSION_ACTIVE_PLOT_KEY,
        SESSION_USER_PROFILE_KEY,
        SESSION_RECENT_EXPORTS_KEY,
        SESSION_WINDOW_LAYOUT_KEY,
        SESSION_LAST_RESTORED_KEY,
        SESSION_LAST_SAVED_KEY,
    )
