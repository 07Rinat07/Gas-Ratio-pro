"""Modern Workbench shell model.

The shell model describes what the UI should render, but it does not import or
call Streamlit.  This keeps the Workbench sprint aligned with the project rule:
zero business logic in UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, MutableMapping

from core.application_state import ApplicationContext, ApplicationStateController
from core.command_framework import WorkbenchCommand, WorkbenchCommandRegistry, default_workbench_commands
from core.workspace_session import (
    SESSION_ACTIVE_PLOT_KEY,
    SESSION_ACTIVE_REPORT_KEY,
    SESSION_RECENT_EXPORTS_KEY,
    SESSION_WINDOW_LAYOUT_KEY,
)


@dataclass(frozen=True, slots=True)
class WorkbenchPanel:
    """One panel in the workbench shell."""

    id: str
    title: str
    region: str
    visible: bool = True
    order: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "region": self.region,
            "visible": self.visible,
            "order": self.order,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class WorkbenchStatus:
    """Compact status bar payload for the shell footer."""

    project_id: str = ""
    well_id: str = ""
    las_id: str = ""
    workspace_id: str = ""
    active_report: str = ""
    active_plot: str = ""
    recent_exports_count: int = 0

    def ready(self) -> bool:
        return bool(self.project_id or self.workspace_id or self.las_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "well_id": self.well_id,
            "las_id": self.las_id,
            "workspace_id": self.workspace_id,
            "active_report": self.active_report,
            "active_plot": self.active_plot,
            "recent_exports_count": self.recent_exports_count,
            "ready": self.ready(),
        }


@dataclass(frozen=True, slots=True)
class WorkbenchShellModel:
    """Serializable UI-neutral description of the Modern Workbench."""

    context: ApplicationContext
    panels: tuple[WorkbenchPanel, ...]
    commands: tuple[WorkbenchCommand, ...]
    status: WorkbenchStatus
    layout: dict[str, Any] = field(default_factory=dict)

    def panel_ids(self) -> tuple[str, ...]:
        return tuple(panel.id for panel in self.panels if panel.visible)

    def command_ids(self) -> tuple[str, ...]:
        return tuple(command.id for command in self.commands if command.visible)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "panels": [panel.to_dict() for panel in self.panels],
            "commands": [command.to_dict() for command in self.commands],
            "status": self.status.to_dict(),
            "layout": dict(self.layout),
        }


DEFAULT_WORKBENCH_PANELS: tuple[WorkbenchPanel, ...] = (
    WorkbenchPanel("project_explorer", "Project Explorer", "left", order=10),
    WorkbenchPanel("workspace_toolbar", "Workspace Toolbar", "top", order=20),
    WorkbenchPanel("workspace_area", "Workspace Area", "center", order=30),
    WorkbenchPanel("properties", "Properties", "right", order=40),
    WorkbenchPanel("status_bar", "Status", "bottom", order=50),
)


class WorkbenchShellBuilder:
    """Build the Modern Workbench shell from application state."""

    def __init__(self, state: MutableMapping[str, Any], *, command_registry: WorkbenchCommandRegistry | None = None) -> None:
        self.state = state
        self.state_controller = ApplicationStateController(state)
        self.command_registry = command_registry or WorkbenchCommandRegistry(state)
        if not self.command_registry.list(visible_only=False):
            self.command_registry.register_many(default_workbench_commands())

    def build(self, panels: Iterable[WorkbenchPanel] | None = None) -> WorkbenchShellModel:
        context = self.state_controller.context()
        panel_list = tuple(sorted(tuple(panels or DEFAULT_WORKBENCH_PANELS), key=lambda item: (item.order, item.id)))
        status = WorkbenchStatus(
            project_id=context.project_id,
            well_id=context.well_id,
            las_id=context.las_id,
            workspace_id=context.workspace_id,
            active_report=str(self.state.get(SESSION_ACTIVE_REPORT_KEY, "") or ""),
            active_plot=str(self.state.get(SESSION_ACTIVE_PLOT_KEY, "") or ""),
            recent_exports_count=len(tuple(self.state.get(SESSION_RECENT_EXPORTS_KEY, ()) or ())),
        )
        layout = dict(self.state.get(SESSION_WINDOW_LAYOUT_KEY, {}) or {})
        return WorkbenchShellModel(
            context=context,
            panels=panel_list,
            commands=self.command_registry.list(),
            status=status,
            layout=layout,
        )
