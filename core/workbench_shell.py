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
from core.event_bus import ApplicationEventBus
from core.workbench_tools import (
    WORKBENCH_ACTIVATE_TOOL_COMMAND_ID,
    WorkbenchToolDescriptor,
    WorkbenchToolManager,
    register_workbench_tool_commands,
)
from core.workspace_session import (
    SESSION_ACTIVE_PLOT_KEY,
    SESSION_ACTIVE_REPORT_KEY,
    SESSION_RECENT_EXPORTS_KEY,
    SESSION_WINDOW_LAYOUT_KEY,
)

WORKBENCH_NAVIGATION_KEY = "workbench_navigation"
WORKBENCH_DOCK_LAYOUT_KEY = "workbench_dock_layout"
WORKBENCH_ACTIVE_NAVIGATION_KEY = "workbench_active_navigation"
WORKBENCH_ACTIVE_DOCK_PANE_KEY = "workbench_active_dock_pane"
WORKBENCH_SELECT_NAVIGATION_COMMAND_ID = "workbench.navigation.select"
WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID = "workbench.dock.activate"


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
class WorkbenchNavigationItem:
    """Serializable navigation entry for the future Workbench sidebar."""

    id: str
    title: str
    workspace: str
    group: str = "workspace"
    icon: str = ""
    order: int = 0
    enabled: bool = True
    visible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "WorkbenchNavigationItem":
        clean_id = str(self.id or "").strip()
        if not clean_id:
            raise ValueError("Navigation item id must not be empty.")
        clean_title = str(self.title or "").strip()
        if not clean_title:
            raise ValueError("Navigation item title must not be empty.")
        clean_workspace = str(self.workspace or "").strip()
        if not clean_workspace:
            raise ValueError("Navigation item workspace must not be empty.")
        return WorkbenchNavigationItem(
            id=clean_id,
            title=clean_title,
            workspace=clean_workspace,
            group=str(self.group or "workspace").strip() or "workspace",
            icon=str(self.icon or "").strip(),
            order=int(self.order or 0),
            enabled=bool(self.enabled),
            visible=bool(self.visible),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        item = self.normalized()
        return {
            "id": item.id,
            "title": item.title,
            "workspace": item.workspace,
            "group": item.group,
            "icon": item.icon,
            "order": item.order,
            "enabled": item.enabled,
            "visible": item.visible,
            "metadata": dict(item.metadata),
        }


@dataclass(frozen=True, slots=True)
class WorkbenchDockPane:
    """Framework-neutral dock pane description.

    The pane stores layout intent only.  Width, height and collapsed state are
    safe to persist in session state because they are rendering preferences, not
    domain decisions.
    """

    id: str
    panel_id: str
    region: str
    title: str = ""
    order: int = 0
    size: int | None = None
    collapsed: bool = False
    floating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "WorkbenchDockPane":
        clean_id = str(self.id or "").strip()
        if not clean_id:
            raise ValueError("Dock pane id must not be empty.")
        clean_panel_id = str(self.panel_id or "").strip()
        if not clean_panel_id:
            raise ValueError("Dock pane panel id must not be empty.")
        clean_region = str(self.region or "").strip() or "center"
        return WorkbenchDockPane(
            id=clean_id,
            panel_id=clean_panel_id,
            region=clean_region,
            title=str(self.title or "").strip() or clean_panel_id.replace("_", " ").title(),
            order=int(self.order or 0),
            size=self.size if self.size is None else int(self.size),
            collapsed=bool(self.collapsed),
            floating=bool(self.floating),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        pane = self.normalized()
        return {
            "id": pane.id,
            "panel_id": pane.panel_id,
            "region": pane.region,
            "title": pane.title,
            "order": pane.order,
            "size": pane.size,
            "collapsed": pane.collapsed,
            "floating": pane.floating,
            "metadata": dict(pane.metadata),
        }


@dataclass(frozen=True, slots=True)
class WorkbenchDockLayout:
    """Serializable dock layout grouped by region."""

    panes: tuple[WorkbenchDockPane, ...]

    def region(self, name: str) -> tuple[WorkbenchDockPane, ...]:
        clean_name = str(name or "").strip()
        return tuple(pane for pane in self.panes if pane.region == clean_name and not pane.collapsed)

    def pane_ids(self) -> tuple[str, ...]:
        return tuple(pane.id for pane in self.panes)

    def to_dict(self) -> dict[str, Any]:
        panes = tuple(sorted((pane.normalized() for pane in self.panes), key=lambda item: (item.region, item.order, item.id)))
        return {
            "panes": [pane.to_dict() for pane in panes],
            "regions": {
                region: [pane.id for pane in panes if pane.region == region and not pane.collapsed]
                for region in sorted({pane.region for pane in panes})
            },
        }




@dataclass(frozen=True, slots=True)
class WorkbenchInteractionState:
    """Serializable transient Workbench UI state.

    The state stores only user-interface selection intent: which navigation item
    is active and which dock pane currently has focus.  It deliberately does
    not store calculations, LAS parsing results, interpretation decisions or
    export data, so the UI can restore its view without owning business logic.
    """

    active_navigation_id: str = ""
    active_workspace: str = ""
    active_dock_pane_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_navigation_id": self.active_navigation_id,
            "active_workspace": self.active_workspace,
            "active_dock_pane_id": self.active_dock_pane_id,
        }


def _choose_active_navigation_id(state: MutableMapping[str, Any], navigation: Iterable[WorkbenchNavigationItem]) -> str:
    visible_enabled = tuple(item for item in navigation if item.visible and item.enabled)
    requested = str(state.get(WORKBENCH_ACTIVE_NAVIGATION_KEY, "") or "").strip()
    if requested and any(item.id == requested for item in visible_enabled):
        return requested
    return visible_enabled[0].id if visible_enabled else ""


def _choose_active_dock_pane_id(state: MutableMapping[str, Any], dock_layout: WorkbenchDockLayout) -> str:
    visible_panes = tuple(pane for pane in dock_layout.panes if not pane.collapsed)
    requested = str(state.get(WORKBENCH_ACTIVE_DOCK_PANE_KEY, "") or "").strip()
    if requested and any(pane.id == requested for pane in visible_panes):
        return requested
    center_panes = tuple(pane for pane in visible_panes if pane.region == "center")
    if center_panes:
        return center_panes[0].id
    return visible_panes[0].id if visible_panes else ""


def _build_interaction_state(
    state: MutableMapping[str, Any],
    navigation: Iterable[WorkbenchNavigationItem],
    dock_layout: WorkbenchDockLayout,
) -> WorkbenchInteractionState:
    navigation_items = tuple(navigation)
    active_navigation_id = _choose_active_navigation_id(state, navigation_items)
    active_navigation = next((item for item in navigation_items if item.id == active_navigation_id), None)
    return WorkbenchInteractionState(
        active_navigation_id=active_navigation_id,
        active_workspace=active_navigation.workspace if active_navigation is not None else "",
        active_dock_pane_id=_choose_active_dock_pane_id(state, dock_layout),
    )


def select_workbench_navigation(state: MutableMapping[str, Any], navigation_id: str) -> None:
    """Persist the currently selected Workbench navigation entry."""

    clean_id = str(navigation_id or "").strip()
    if not clean_id:
        raise ValueError("Navigation id must not be empty.")
    state[WORKBENCH_ACTIVE_NAVIGATION_KEY] = clean_id


def activate_workbench_dock_pane(state: MutableMapping[str, Any], pane_id: str) -> None:
    """Persist the currently focused Workbench dock pane."""

    clean_id = str(pane_id or "").strip()
    if not clean_id:
        raise ValueError("Dock pane id must not be empty.")
    state[WORKBENCH_ACTIVE_DOCK_PANE_KEY] = clean_id


def register_workbench_interaction_commands(
    state: MutableMapping[str, Any],
    registry: WorkbenchCommandRegistry | None = None,
) -> WorkbenchCommandRegistry:
    """Register state-changing Workbench commands.

    The future UI must call these commands instead of mutating Workbench state
    directly.  This keeps navigation clicks, dock focus changes and keyboard
    shortcuts on the same command/event path.
    """

    command_registry = registry or WorkbenchCommandRegistry(state)

    def _select_navigation(payload: dict[str, Any]) -> dict[str, str]:
        navigation_id = str(payload.get("navigation_id") or payload.get("id") or "").strip()
        select_workbench_navigation(state, navigation_id)
        ApplicationEventBus(state).publish(
            "workbench.navigation.changed",
            {"active_navigation_id": state[WORKBENCH_ACTIVE_NAVIGATION_KEY]},
            source="WorkbenchCommandRegistry",
        )
        return {
            "active_navigation_id": state[WORKBENCH_ACTIVE_NAVIGATION_KEY],
        }

    def _activate_dock_pane(payload: dict[str, Any]) -> dict[str, str]:
        pane_id = str(payload.get("pane_id") or payload.get("id") or "").strip()
        activate_workbench_dock_pane(state, pane_id)
        ApplicationEventBus(state).publish(
            "workbench.active_panel.changed",
            {"active_dock_pane_id": state[WORKBENCH_ACTIVE_DOCK_PANE_KEY]},
            source="WorkbenchCommandRegistry",
        )
        return {
            "active_dock_pane_id": state[WORKBENCH_ACTIVE_DOCK_PANE_KEY],
        }

    command_registry.register(
        WorkbenchCommand(
            WORKBENCH_SELECT_NAVIGATION_COMMAND_ID,
            "Выбрать раздел Workbench",
            "workbench",
            "Сменить активный раздел навигации через command layer.",
            payload={},
        ),
        _select_navigation,
        replace=True,
    )
    command_registry.register(
        WorkbenchCommand(
            WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID,
            "Активировать панель Workbench",
            "workbench",
            "Сменить активную dock-панель через command layer.",
            payload={},
        ),
        _activate_dock_pane,
        replace=True,
    )
    return command_registry


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
    navigation: tuple[WorkbenchNavigationItem, ...] = field(default_factory=tuple)
    dock_layout: WorkbenchDockLayout = field(default_factory=lambda: WorkbenchDockLayout(()))
    interaction: WorkbenchInteractionState = field(default_factory=WorkbenchInteractionState)
    tools: tuple[WorkbenchToolDescriptor, ...] = field(default_factory=tuple)
    active_tool_id: str = ""
    open_tool_ids: tuple[str, ...] = field(default_factory=tuple)

    def panel_ids(self) -> tuple[str, ...]:
        return tuple(panel.id for panel in self.panels if panel.visible)

    def command_ids(self) -> tuple[str, ...]:
        return tuple(command.id for command in self.commands if command.visible)

    def navigation_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.navigation if item.visible)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "panels": [panel.to_dict() for panel in self.panels],
            "commands": [command.to_dict() for command in self.commands],
            "status": self.status.to_dict(),
            "layout": dict(self.layout),
            "navigation": [item.to_dict() for item in self.navigation],
            "dock_layout": self.dock_layout.to_dict(),
            "interaction": self.interaction.to_dict(),
            "tools": [tool.to_dict() for tool in self.tools if tool.visible],
            "active_tool_id": self.active_tool_id,
            "open_tool_ids": list(self.open_tool_ids),
        }


@dataclass(frozen=True, slots=True)
class WorkbenchRendererAction:
    """UI-facing action descriptor for renderer adapters.

    Renderer actions are intentionally declarative.  A Streamlit, desktop or web
    renderer can show buttons, links or keyboard shortcuts from this payload and
    submit only the command id plus user-provided payload back to the command
    framework.  No renderer needs to know how navigation or dock state is
    persisted.
    """

    id: str
    command_id: str
    title: str
    target: str
    payload_schema: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "WorkbenchRendererAction":
        clean_id = str(self.id or "").strip()
        if not clean_id:
            raise ValueError("Renderer action id must not be empty.")
        clean_command_id = str(self.command_id or "").strip()
        if not clean_command_id:
            raise ValueError("Renderer action command id must not be empty.")
        clean_title = str(self.title or "").strip()
        if not clean_title:
            raise ValueError("Renderer action title must not be empty.")
        clean_target = str(self.target or "").strip() or "workbench"
        return WorkbenchRendererAction(
            id=clean_id,
            command_id=clean_command_id,
            title=clean_title,
            target=clean_target,
            payload_schema=dict(self.payload_schema or {}),
            enabled=bool(self.enabled),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        action = self.normalized()
        return {
            "id": action.id,
            "command_id": action.command_id,
            "title": action.title,
            "target": action.target,
            "payload_schema": dict(action.payload_schema),
            "enabled": action.enabled,
            "metadata": dict(action.metadata),
        }


@dataclass(frozen=True, slots=True)
class WorkbenchRendererContract:
    """Stable payload consumed by future Workbench UI renderers.

    The contract is narrower than the full shell model: it contains the exact
    renderer-facing navigation, dock regions, status, command palette and
    allowed interaction actions.  It deliberately excludes handlers, storage
    objects and calculation data, so the UI boundary remains presentation-only.
    """

    version: str
    renderer: str
    shell: WorkbenchShellModel
    actions: tuple[WorkbenchRendererAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "renderer": self.renderer,
            "context": self.shell.context.to_dict(),
            "status": self.shell.status.to_dict(),
            "navigation": [item.to_dict() for item in self.shell.navigation if item.visible],
            "dock_regions": self.shell.dock_layout.to_dict()["regions"],
            "panels": [panel.to_dict() for panel in self.shell.panels if panel.visible],
            "commands": [command.to_dict() for command in self.shell.commands if command.visible],
            "interaction": self.shell.interaction.to_dict(),
            "tools": [tool.to_dict() for tool in self.shell.tools if tool.visible],
            "active_tool_id": self.shell.active_tool_id,
            "open_tool_ids": list(self.shell.open_tool_ids),
            "actions": [action.to_dict() for action in self.actions],
        }

    def action_ids(self) -> tuple[str, ...]:
        return tuple(action.normalized().id for action in self.actions if action.enabled)


def build_workbench_renderer_contract(
    shell: WorkbenchShellModel,
    *,
    renderer: str = "streamlit",
    version: str = "workbench-renderer-contract",
) -> WorkbenchRendererContract:
    """Build a framework-neutral renderer contract from the shell model."""

    actions = (
        WorkbenchRendererAction(
            "action.select_navigation",
            WORKBENCH_SELECT_NAVIGATION_COMMAND_ID,
            "Выбрать раздел",
            "navigation",
            payload_schema={"navigation_id": "string"},
            metadata={"active_navigation_id": shell.interaction.active_navigation_id},
        ),
        WorkbenchRendererAction(
            "action.activate_dock_pane",
            WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID,
            "Активировать панель",
            "dock",
            payload_schema={"pane_id": "string"},
            metadata={"active_dock_pane_id": shell.interaction.active_dock_pane_id},
        ),
        WorkbenchRendererAction(
            "action.activate_tool",
            WORKBENCH_ACTIVATE_TOOL_COMMAND_ID,
            "Активировать инструмент",
            "tool",
            payload_schema={"tool_id": "string"},
            metadata={"active_tool_id": shell.active_tool_id},
        ),
    )
    return WorkbenchRendererContract(
        version=str(version or "workbench-renderer-contract").strip() or "workbench-renderer-contract",
        renderer=str(renderer or "streamlit").strip() or "streamlit",
        shell=shell,
        actions=actions,
    )


DEFAULT_WORKBENCH_PANELS: tuple[WorkbenchPanel, ...] = (
    WorkbenchPanel("project_explorer", "Project Explorer", "left", order=10),
    WorkbenchPanel("workspace_toolbar", "Workspace Toolbar", "top", order=20),
    WorkbenchPanel("workspace_area", "Workspace Area", "center", order=30),
    WorkbenchPanel("properties", "Properties", "right", order=40),
    WorkbenchPanel("status_bar", "Status", "bottom", order=50),
)

DEFAULT_WORKBENCH_NAVIGATION: tuple[WorkbenchNavigationItem, ...] = (
    WorkbenchNavigationItem("nav.dashboard", "Dashboard", "dashboard", "main", "dashboard", order=10),
    WorkbenchNavigationItem("nav.las_workspace", "LAS Workspace", "las_workspace", "main", "well", order=20),
    WorkbenchNavigationItem("nav.interpretation", "Interpretation", "interpretation", "analysis", "ratio", order=30),
    WorkbenchNavigationItem("nav.reports", "Reports", "reports", "output", "report", order=40),
    WorkbenchNavigationItem("nav.exports", "Exports", "exports", "output", "export", order=50),
)

DEFAULT_WORKBENCH_DOCK_PANES: tuple[WorkbenchDockPane, ...] = (
    WorkbenchDockPane("dock.project_explorer", "project_explorer", "left", "Project Explorer", order=10, size=280),
    WorkbenchDockPane("dock.workspace_toolbar", "workspace_toolbar", "top", "Workspace Toolbar", order=20, size=64),
    WorkbenchDockPane("dock.workspace_area", "workspace_area", "center", "Workspace Area", order=30),
    WorkbenchDockPane("dock.properties", "properties", "right", "Properties", order=40, size=320),
    WorkbenchDockPane("dock.status_bar", "status_bar", "bottom", "Status", order=50, size=36),
)


def _build_navigation(state: MutableMapping[str, Any], defaults: Iterable[WorkbenchNavigationItem]) -> tuple[WorkbenchNavigationItem, ...]:
    raw_items = state.get(WORKBENCH_NAVIGATION_KEY)
    if raw_items:
        items = [WorkbenchNavigationItem(**dict(item)) for item in raw_items]
    else:
        items = list(defaults)
    return tuple(sorted((item.normalized() for item in items), key=lambda item: (item.order, item.group, item.id)))


def _build_dock_layout(state: MutableMapping[str, Any], defaults: Iterable[WorkbenchDockPane]) -> WorkbenchDockLayout:
    raw_panes = state.get(WORKBENCH_DOCK_LAYOUT_KEY)
    if raw_panes:
        panes = [WorkbenchDockPane(**dict(item)) for item in raw_panes]
    else:
        panes = list(defaults)
    return WorkbenchDockLayout(tuple(sorted((pane.normalized() for pane in panes), key=lambda item: (item.region, item.order, item.id))))


class WorkbenchShellBuilder:
    """Build the Modern Workbench shell from application state."""

    def __init__(self, state: MutableMapping[str, Any], *, command_registry: WorkbenchCommandRegistry | None = None) -> None:
        self.state = state
        self.state_controller = ApplicationStateController(state)
        self.command_registry = command_registry or WorkbenchCommandRegistry(state)
        if not self.command_registry.list(visible_only=False):
            self.command_registry.register_many(default_workbench_commands())
        register_workbench_interaction_commands(self.state, self.command_registry)
        register_workbench_tool_commands(self.state, self.command_registry)
        from core.workbench_tool_actions import register_workbench_tool_action_commands
        register_workbench_tool_action_commands(self.state, self.command_registry)

    def build(
        self,
        panels: Iterable[WorkbenchPanel] | None = None,
        navigation: Iterable[WorkbenchNavigationItem] | None = None,
        dock_panes: Iterable[WorkbenchDockPane] | None = None,
    ) -> WorkbenchShellModel:
        context = self.state_controller.context()
        panel_list = tuple(sorted(tuple(panels or DEFAULT_WORKBENCH_PANELS), key=lambda item: (item.order, item.id)))
        navigation_items = tuple(sorted((item.normalized() for item in (navigation or _build_navigation(self.state, DEFAULT_WORKBENCH_NAVIGATION))), key=lambda item: (item.order, item.group, item.id)))
        dock_layout = _build_dock_layout(self.state, dock_panes or DEFAULT_WORKBENCH_DOCK_PANES)
        interaction = _build_interaction_state(self.state, navigation_items, dock_layout)
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
        tool_manager = WorkbenchToolManager(self.state)
        tool_summary = tool_manager.summary()
        tools = tuple(WorkbenchToolDescriptor.from_dict(item) for item in tool_summary["tools"])
        return WorkbenchShellModel(
            context=context,
            panels=panel_list,
            commands=self.command_registry.list(),
            status=status,
            layout=layout,
            navigation=navigation_items,
            dock_layout=dock_layout,
            interaction=interaction,
            tools=tools,
            active_tool_id=str(tool_summary["active_tool_id"] or ""),
            open_tool_ids=tuple(tool_summary["open_tool_ids"]),
        )
