"""Renderer-facing view models for Workbench tools.

The tool view layer translates registered tools and current Workbench state into
small serializable payloads.  It intentionally contains no Streamlit imports and
no engineering calculations.  Renderers receive these view models, display them,
and send actions back to the controller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, MutableMapping

from core.workbench_context import WorkspaceContext
from core.workbench_tools import WorkbenchToolDescriptor, WorkbenchToolManager, WorkbenchToolRegistry


@dataclass(frozen=True, slots=True)
class WorkbenchToolViewModel:
    """Serializable renderer contract for one Workbench tool."""

    id: str
    title: str
    category: str
    icon: str = ""
    active: bool = False
    open: bool = False
    enabled: bool = True
    supported_targets: tuple[str, ...] = field(default_factory=tuple)
    status: str = "available"
    empty_state: str = ""
    renderer_hint: str = "placeholder"
    actions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible payload for UI renderers."""

        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "icon": self.icon,
            "active": self.active,
            "open": self.open,
            "enabled": self.enabled,
            "supported_targets": list(self.supported_targets),
            "status": self.status,
            "empty_state": self.empty_state,
            "renderer_hint": self.renderer_hint,
            "actions": [dict(action) for action in self.actions],
            "metadata": dict(self.metadata),
        }


def _default_empty_state(tool: WorkbenchToolDescriptor, context: WorkspaceContext) -> str:
    """Build a human-readable empty state without touching domain services."""

    if tool.id == "tool.las_viewer":
        return "Open or import a LAS file to inspect curves."
    if tool.id == "tool.log_viewer":
        return "Select a LAS curve to preview log tracks."
    if tool.id == "tool.gas_ratio_analysis":
        return "Select an interval with gas data to run gas ratio interpretation."
    if tool.id == "tool.report_preview":
        return "Generate or select an engineering report to preview it."
    if tool.id == "tool.export":
        return "Create an engineering report before exporting HTML PDF or DOCX."
    if tool.id == "tool.settings":
        return "Configure workspace presentation and reporting options."
    if context.application.workspace_id:
        return "Workspace tool is ready."
    return "Open a workspace to use this tool."


def _tool_status(tool: WorkbenchToolDescriptor, context: WorkspaceContext) -> str:
    """Return lightweight readiness status based on context only."""

    if not tool.enabled:
        return "disabled"
    targets = set(tool.supported_targets)
    if "las" in targets and not context.application.las_id:
        return "waiting_for_las"
    if "report" in targets and not context.active_report:
        return "waiting_for_report"
    if "workspace" in targets and not context.application.workspace_id:
        return "waiting_for_workspace"
    return "ready"


def _renderer_hint(tool: WorkbenchToolDescriptor) -> str:
    mapping = {
        "tool.workspace_explorer": "tree",
        "tool.las_viewer": "las_curve_viewer",
        "tool.log_viewer": "log_track_viewer",
        "tool.gas_ratio_analysis": "interpretation_panel",
        "tool.report_preview": "report_preview",
        "tool.export": "export_panel",
        "tool.settings": "settings_panel",
    }
    return mapping.get(tool.id, str(tool.factory or "placeholder") or "placeholder")


def build_tool_view_model(
    tool: WorkbenchToolDescriptor,
    *,
    active_tool_id: str,
    open_tool_ids: Iterable[str],
    context: WorkspaceContext,
) -> WorkbenchToolViewModel:
    """Create one renderer-facing view model from a tool descriptor."""

    opened = set(open_tool_ids)
    status = _tool_status(tool, context)
    metadata = dict(tool.metadata or {})
    metadata.update({"factory": tool.factory, "order": tool.order})
    actions = (
        {
            "id": "action.activate_tool",
            "title": "Activate tool",
            "payload": {"tool_id": tool.id},
            "enabled": bool(tool.enabled),
        },
    )
    return WorkbenchToolViewModel(
        id=tool.id,
        title=tool.title,
        category=tool.category,
        icon=tool.icon,
        active=tool.id == active_tool_id,
        open=tool.id in opened,
        enabled=tool.enabled,
        supported_targets=tuple(tool.supported_targets),
        status=status,
        empty_state=_default_empty_state(tool, context),
        renderer_hint=_renderer_hint(tool),
        actions=actions,
        metadata=metadata,
    )


class WorkbenchToolViewService:
    """Build tool view models for the controller and renderer contract."""

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state
        self.registry = WorkbenchToolRegistry(state)
        self.manager = WorkbenchToolManager(state, self.registry)

    def build_all(self, context: WorkspaceContext) -> tuple[WorkbenchToolViewModel, ...]:
        active = self.manager.active_tool_id()
        opened = self.manager.open_tool_ids()
        return tuple(
            build_tool_view_model(tool, active_tool_id=active, open_tool_ids=opened, context=context)
            for tool in self.registry.list()
        )

    def active(self, context: WorkspaceContext) -> WorkbenchToolViewModel | None:
        active_id = self.manager.active_tool_id()
        for view in self.build_all(context):
            if view.id == active_id:
                return view
        return None

    def payload(self, context: WorkspaceContext) -> dict[str, Any]:
        views = self.build_all(context)
        active = next((view for view in views if view.active), None)
        return {
            "active_tool_id": active.id if active is not None else "",
            "active_tool": active.to_dict() if active is not None else None,
            "items": [view.to_dict() for view in views],
            "open_tool_ids": [view.id for view in views if view.open],
        }
