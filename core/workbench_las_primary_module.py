"""Primary LAS Viewer module lifecycle for Modern Workbench.

This application-layer boundary coordinates the active LAS context with the
Workbench module/tool/dock state and exposes renderer-neutral navigation,
interaction and export commands. UI adapters receive only serializable
contracts and never parse LAS files or execute engineering calculations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping

from core.application_state import ApplicationStateController
from core.command_framework import WorkbenchCommand, WorkbenchCommandRegistry
from core.event_bus import ApplicationEventBus
from core.workbench_context import WorkspaceContext, WorkbenchSelectionService
from core.workbench_tools import WorkbenchToolManager
from core.workbench_shell import WORKBENCH_ACTIVE_NAVIGATION_KEY, WorkbenchDockManager
from services.las_visualization_payload_service import LasVisualizationPayloadService
from services.las_viewer_export import LasViewerExportService
from services.las_viewer_navigation import LasViewerNavigationController
from services.las_viewer_session import LasViewerSession
from services.las_viewer_shared_interaction import LasViewerSharedInteractionController
from services.visualization_cursor import CursorRequest
from services.visualization_selection import SelectionCommand

LAS_PRIMARY_ACTIVATE = "workbench.las.primary.activate"
LAS_PRIMARY_ZOOM = "workbench.las.primary.zoom"
LAS_PRIMARY_PAN = "workbench.las.primary.pan"
LAS_PRIMARY_FIT = "workbench.las.primary.fit"
LAS_PRIMARY_RESET = "workbench.las.primary.reset"
LAS_PRIMARY_CURSOR = "workbench.las.primary.cursor"
LAS_PRIMARY_SELECTION = "workbench.las.primary.selection"
LAS_PRIMARY_EXPORT = "workbench.las.primary.export"

LAS_PRIMARY_STATE_KEY = "workbench_las_primary_state"
LAS_PRIMARY_LAST_EXPORT_KEY = "workbench_las_primary_last_export"


@dataclass(frozen=True, slots=True)
class WorkbenchLasPrimarySnapshot:
    status: str
    project_id: str
    las_id: str
    viewer_state: dict[str, Any]
    last_operation: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "workbench.las.primary-module",
            "version": "1.0",
            "status": self.status,
            "project_id": self.project_id,
            "las_id": self.las_id,
            "viewer_state": dict(self.viewer_state),
            "last_operation": self.last_operation,
            "error": self.error,
            "primary_module": True,
            "renderer_neutral": True,
            "raw_dataframe_included": False,
        }


class WorkbenchLasPrimaryModuleService:
    """Coordinate LAS Viewer lifecycle without leaking storage into the UI."""

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state
        self.events = ApplicationEventBus(state)

    def _context(self) -> WorkspaceContext:
        return WorkspaceContext.from_state(self.state)

    def _root(self) -> str:
        return str(self.state.get("projects_root") or self.state.get("project_root") or "projects")

    def _payload(self, project_id: str, las_id: str) -> dict[str, Any]:
        return LasVisualizationPayloadService(self._root()).build(project_id, las_id).to_dict()

    def _persist(self, snapshot: WorkbenchLasPrimarySnapshot) -> dict[str, Any]:
        payload = snapshot.to_dict()
        self.state[LAS_PRIMARY_STATE_KEY] = dict(payload)
        self.events.publish("workbench.las.primary.state_changed", payload, source=type(self).__name__)
        return dict(payload)

    def snapshot(self) -> dict[str, Any]:
        stored = self.state.get(LAS_PRIMARY_STATE_KEY)
        if isinstance(stored, dict):
            return dict(stored)
        context = self._context()
        return WorkbenchLasPrimarySnapshot(
            status="waiting_for_las",
            project_id=context.application.project_id,
            las_id=context.application.las_id,
            viewer_state={},
        ).to_dict()

    def activate(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = dict(payload or {})
        context = self._context()
        project_id = str(request.get("project_id") or context.application.project_id or "").strip()
        las_id = str(request.get("las_id") or context.application.las_id or "").strip()
        if not project_id or not las_id:
            return self._persist(WorkbenchLasPrimarySnapshot("waiting_for_las", project_id, las_id, {}, "activate", "Select a project and LAS."))
        ApplicationStateController(self.state).activate_las(las_id)
        WorkbenchSelectionService(self.state).select("las", las_id, {"source": "workbench_las_primary"})
        tool_manager = WorkbenchToolManager(self.state)
        tool_manager.activate("tool.las_viewer", {"primary_module": True, "las_id": las_id})
        self.state[WORKBENCH_ACTIVE_NAVIGATION_KEY] = "nav.las_workspace"
        dock_manager = WorkbenchDockManager(self.state)
        dock_manager.ensure_tool_panes(tool_manager.registry.list(), tool_manager.open_tool_ids())
        dock_manager.open("dock.tool.las_viewer")
        viewer_state = LasViewerSession(self._payload(project_id, las_id)).state.to_dict()
        return self._persist(WorkbenchLasPrimarySnapshot("ready", project_id, las_id, viewer_state, "activate"))

    def _controller(self) -> tuple[LasViewerNavigationController, str, str]:
        current = self.snapshot()
        project_id = str(current.get("project_id") or "")
        las_id = str(current.get("las_id") or "")
        if not project_id or not las_id:
            raise ValueError("Primary LAS Viewer module is not active.")
        payload = self._payload(project_id, las_id)
        state = current.get("viewer_state") or {}
        viewer = LasViewerSession.from_state(state) if state else LasViewerSession(payload)
        interaction = LasViewerSharedInteractionController(payload, viewer)
        return LasViewerNavigationController(payload, interaction_controller=interaction), project_id, las_id

    def navigate(self, operation: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = dict(payload or {})
        controller, project_id, las_id = self._controller()
        if operation == "zoom":
            result = controller.zoom(float(request.get("factor", 1.0)), anchor_depth=request.get("anchor_depth"))
        elif operation == "pan":
            result = controller.pan_depth(float(request.get("delta", 0.0)))
        elif operation == "fit":
            if request.get("start") is None or request.get("stop") is None:
                result = controller.fit()
            else:
                result = controller.fit(float(request["start"]), float(request["stop"]))
        elif operation == "reset":
            result = controller.reset()
        else:
            raise KeyError(operation)
        snapshot = WorkbenchLasPrimarySnapshot("ready", project_id, las_id, dict(result.interaction.viewer_state), operation)
        output = self._persist(snapshot)
        output["navigation"] = result.to_dict()
        return output

    def cursor(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = dict(payload or {})
        controller, project_id, las_id = self._controller()
        interaction = controller.interaction_controller
        if request.get("clear"):
            result = interaction.clear_cursor()
        else:
            result = interaction.update_cursor(CursorRequest(
                x=float(request.get("x", 0.0)),
                y=float(request.get("y", 0.0)),
                tolerance=float(request.get("tolerance", 6.0)),
                track_id=str(request.get("track_id", "") or ""),
                max_results=int(request.get("max_results", 8)),
                clamp_depth=bool(request.get("clamp_depth", True)),
            ))
        output = self._persist(WorkbenchLasPrimarySnapshot("ready", project_id, las_id, dict(result.viewer_state), "cursor"))
        output["interaction"] = result.to_dict()
        return output

    def selection(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        controller, project_id, las_id = self._controller()
        result = controller.interaction_controller.execute_selection(SelectionCommand.from_dict(dict(payload or {})))
        output = self._persist(WorkbenchLasPrimarySnapshot("ready", project_id, las_id, dict(result.viewer_state), "selection"))
        output["interaction"] = result.to_dict()
        return output

    def export(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        controller, project_id, las_id = self._controller()
        bundle = LasViewerExportService().export_current_view(controller)
        summary = bundle.to_dict()
        self.state[LAS_PRIMARY_LAST_EXPORT_KEY] = summary
        self.events.publish("workbench.las.primary.exported", {"project_id": project_id, "las_id": las_id, "export": summary}, source=type(self).__name__)
        return {"project_id": project_id, "las_id": las_id, "export": summary, "raw_dataframe_included": False}


def register_workbench_las_primary_commands(state: MutableMapping[str, Any], registry: WorkbenchCommandRegistry | None = None) -> WorkbenchCommandRegistry:
    command_registry = registry or WorkbenchCommandRegistry(state)
    service = WorkbenchLasPrimaryModuleService(state)
    entries = (
        (LAS_PRIMARY_ACTIVATE, "Activate primary LAS Viewer", service.activate),
        (LAS_PRIMARY_ZOOM, "Zoom primary LAS Viewer", lambda payload: service.navigate("zoom", payload)),
        (LAS_PRIMARY_PAN, "Pan primary LAS Viewer", lambda payload: service.navigate("pan", payload)),
        (LAS_PRIMARY_FIT, "Fit primary LAS Viewer", lambda payload: service.navigate("fit", payload)),
        (LAS_PRIMARY_RESET, "Reset primary LAS Viewer", lambda payload: service.navigate("reset", payload)),
        (LAS_PRIMARY_CURSOR, "Update LAS Viewer cursor", service.cursor),
        (LAS_PRIMARY_SELECTION, "Update LAS Viewer selection", service.selection),
        (LAS_PRIMARY_EXPORT, "Export current LAS Viewer", service.export),
    )
    for command_id, title, handler in entries:
        command_registry.register(WorkbenchCommand(command_id, title, "las_viewer", title + " through application services."), handler, replace=True)
    return command_registry
