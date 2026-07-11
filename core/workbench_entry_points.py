"""Project and recent-session entry points for the Modern Workbench.

All repository and session-file access is kept behind command handlers. UI
adapters receive serializable descriptors and invoke commands only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, MutableMapping

from core.command_framework import WorkbenchCommand
from core.workbench_controller import WorkbenchController, build_workbench_controller
from core.workspace_session import WorkspaceSessionManager
from projects.recent_projects import list_recent_projects, touch_recent_project
from projects.repository import DEFAULT_PROJECTS_ROOT, load_project

OPEN_PROJECT_COMMAND_ID = "workbench.entry.open_project"
RESTORE_RECENT_SESSION_COMMAND_ID = "workbench.entry.restore_recent_session"
ENTRY_STATE_KEY = "workbench_entry_state"


@dataclass(frozen=True, slots=True)
class WorkbenchEntryResult:
    kind: str
    project_id: str = ""
    session_path: str = ""
    active_navigation_id: str = ""
    active_tool_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "project_id": self.project_id,
            "session_path": self.session_path,
            "active_navigation_id": self.active_navigation_id,
            "active_tool_id": self.active_tool_id,
        }


class WorkbenchEntryPointService:
    """Command-backed project and recent-session entry boundary."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        controller: WorkbenchController | None = None,
        projects_root: str | Path = DEFAULT_PROJECTS_ROOT,
        sessions_dir: str | Path = "data/sessions",
    ) -> None:
        self.state = state
        self.controller = controller or build_workbench_controller(state)
        self.projects_root = Path(projects_root)
        self.sessions_dir = Path(sessions_dir)
        self._register_commands()

    def _register_commands(self) -> None:
        registry = self.controller.command_registry
        registry.register(
            WorkbenchCommand(OPEN_PROJECT_COMMAND_ID, "Открыть проект", "entry", visible=False),
            self._handle_open_project,
            replace=True,
        )
        registry.register(
            WorkbenchCommand(RESTORE_RECENT_SESSION_COMMAND_ID, "Восстановить последнюю сессию", "entry", visible=False),
            self._handle_restore_recent_session,
            replace=True,
        )

    def project_entries(self) -> list[dict[str, Any]]:
        return [
            {
                "project_id": item.project_id,
                "project_name": item.project_name,
                "last_opened_at": item.last_opened_at,
                "available": item.exists_on_disk,
                "action": {"command_id": OPEN_PROJECT_COMMAND_ID, "payload": {"project_id": item.project_id}},
            }
            for item in list_recent_projects(self.projects_root, include_missing=True)
        ]

    def recent_session_entry(self) -> dict[str, Any] | None:
        candidates = sorted(self.sessions_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            return None
        path = candidates[0]
        return {
            "session_path": str(path),
            "action": {"command_id": RESTORE_RECENT_SESSION_COMMAND_ID, "payload": {"session_path": str(path)}},
        }

    def payload(self) -> dict[str, Any]:
        return {
            "projects": self.project_entries(),
            "recent_session": self.recent_session_entry(),
            "actions": {
                "open_project": OPEN_PROJECT_COMMAND_ID,
                "restore_recent_session": RESTORE_RECENT_SESSION_COMMAND_ID,
            },
        }

    def open_project(self, project_id: str) -> WorkbenchEntryResult:
        result = self.controller.command_registry.execute(OPEN_PROJECT_COMMAND_ID, {"project_id": project_id})
        return result.result

    def restore_recent_session(self, session_path: str | Path | None = None) -> WorkbenchEntryResult:
        payload = {} if session_path is None else {"session_path": str(session_path)}
        result = self.controller.command_registry.execute(RESTORE_RECENT_SESSION_COMMAND_ID, payload)
        return result.result

    def _handle_open_project(self, payload: dict[str, Any]) -> WorkbenchEntryResult:
        project_id = str(payload.get("project_id", "")).strip()
        project = load_project(self.projects_root, project_id)
        self.state["active_project_id"] = project.id
        touch_recent_project(self.projects_root, project)
        self.controller.lifecycle().open_workspace()
        navigation = self.controller.select_navigation("nav.dashboard")
        shell = navigation.shell
        result = WorkbenchEntryResult("project", project.id, active_navigation_id=shell.interaction.active_navigation_id, active_tool_id=shell.active_tool_id)
        self.state[ENTRY_STATE_KEY] = result.to_dict()
        return result

    def _handle_restore_recent_session(self, payload: dict[str, Any]) -> WorkbenchEntryResult:
        raw_path = str(payload.get("session_path", "")).strip()
        if raw_path:
            path = Path(raw_path)
        else:
            entry = self.recent_session_entry()
            if entry is None:
                raise FileNotFoundError("No recent Workbench session is available.")
            path = Path(entry["session_path"])
        session = WorkspaceSessionManager(self.state, sessions_dir=self.sessions_dir).load(path)
        self.controller.lifecycle().open_workspace(session)
        navigation_id = session.workbench_active_navigation or "nav.dashboard"
        navigation = self.controller.select_navigation(navigation_id)
        shell = navigation.shell
        result = WorkbenchEntryResult("recent_session", session.project_id, str(path), shell.interaction.active_navigation_id, shell.active_tool_id)
        self.state[ENTRY_STATE_KEY] = result.to_dict()
        return result
