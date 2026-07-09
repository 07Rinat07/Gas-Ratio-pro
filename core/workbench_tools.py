"""Tool registry and activation services for Modern Workbench.

Tools are UI-neutral workbench capabilities such as LAS viewer, report preview
or export.  The registry stores metadata only; activation changes lightweight
session state and publishes events, while actual engineering work remains in
separate domain services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, MutableMapping

from core.command_framework import WorkbenchCommand, WorkbenchCommandRegistry
from core.event_bus import ApplicationEventBus

WORKBENCH_TOOLS_KEY = "workbench_tools"
WORKBENCH_ACTIVE_TOOL_KEY = "workbench_active_tool"
WORKBENCH_OPEN_TOOLS_KEY = "workbench_open_tools"
WORKBENCH_TOOL_ORDER_KEY = "workbench_tool_order"
WORKBENCH_ACTIVATE_TOOL_COMMAND_ID = "workbench.tool.activate"
WORKBENCH_DEACTIVATE_TOOL_COMMAND_ID = "workbench.tool.deactivate"


@dataclass(frozen=True, slots=True)
class WorkbenchToolDescriptor:
    """Serializable metadata for one workbench tool."""

    id: str
    title: str
    category: str = "workspace"
    icon: str = ""
    supported_targets: tuple[str, ...] = ()
    enabled: bool = True
    visible: bool = True
    order: int = 0
    factory: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "WorkbenchToolDescriptor":
        clean_id = str(self.id or "").strip()
        if not clean_id:
            raise ValueError("Tool id must not be empty.")
        clean_title = str(self.title or "").strip()
        if not clean_title:
            raise ValueError("Tool title must not be empty.")
        targets = tuple(str(item or "").strip() for item in self.supported_targets if str(item or "").strip())
        return WorkbenchToolDescriptor(
            id=clean_id,
            title=clean_title,
            category=str(self.category or "workspace").strip() or "workspace",
            icon=str(self.icon or "").strip(),
            supported_targets=targets,
            enabled=bool(self.enabled),
            visible=bool(self.visible),
            order=int(self.order or 0),
            factory=str(self.factory or "").strip(),
            metadata=dict(self.metadata or {}),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkbenchToolDescriptor":
        data = dict(value or {})
        supported = data.get("supported_targets", data.get("targets", ()))
        if isinstance(supported, str):
            supported_targets = (supported,) if supported else ()
        else:
            supported_targets = tuple(str(item or "").strip() for item in (supported or ()) if str(item or "").strip())
        return cls(
            id=str(data.get("id", "") or ""),
            title=str(data.get("title", "") or ""),
            category=str(data.get("category", "workspace") or "workspace"),
            icon=str(data.get("icon", "") or ""),
            supported_targets=supported_targets,
            enabled=bool(data.get("enabled", True)),
            visible=bool(data.get("visible", True)),
            order=int(data.get("order", 0) or 0),
            factory=str(data.get("factory", "") or ""),
            metadata=dict(data.get("metadata", {}) or {}),
        ).normalized()

    def to_dict(self) -> dict[str, Any]:
        tool = self.normalized()
        return {
            "id": tool.id,
            "title": tool.title,
            "category": tool.category,
            "icon": tool.icon,
            "supported_targets": list(tool.supported_targets),
            "enabled": tool.enabled,
            "visible": tool.visible,
            "order": tool.order,
            "factory": tool.factory,
            "metadata": dict(tool.metadata),
        }


DEFAULT_WORKBENCH_TOOLS: tuple[WorkbenchToolDescriptor, ...] = (
    WorkbenchToolDescriptor("tool.workspace_explorer", "Workspace Explorer", "workspace", "folder", ("workspace",), order=10, factory="workspace_explorer"),
    WorkbenchToolDescriptor("tool.las_viewer", "LAS Viewer", "las", "well", ("las", "file"), order=20, factory="las_viewer"),
    WorkbenchToolDescriptor("tool.log_viewer", "Log Viewer", "las", "chart", ("las", "curve"), order=30, factory="log_viewer"),
    WorkbenchToolDescriptor("tool.gas_ratio_analysis", "Gas Ratio Analysis", "interpretation", "ratio", ("las", "interval"), order=40, factory="gas_ratio_analysis"),
    WorkbenchToolDescriptor("tool.report_preview", "Report Preview", "reporting", "report", ("report",), order=50, factory="report_preview"),
    WorkbenchToolDescriptor("tool.export", "Export", "reporting", "export", ("report", "workspace"), order=60, factory="export"),
    WorkbenchToolDescriptor("tool.settings", "Settings", "system", "settings", ("workspace",), order=70, factory="settings"),
)


def _tool_tuple(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, dict))


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Iterable):
        return [str(item or "").strip() for item in value if str(item or "").strip()]
    text = str(value or "").strip()
    return [text] if text else []


class WorkbenchToolRegistry:
    """State-backed metadata registry for workbench tools."""

    def __init__(self, state: MutableMapping[str, Any], defaults: Iterable[WorkbenchToolDescriptor] | None = None) -> None:
        self.state = state
        if not _tool_tuple(state.get(WORKBENCH_TOOLS_KEY)):
            state[WORKBENCH_TOOLS_KEY] = [tool.to_dict() for tool in (defaults or DEFAULT_WORKBENCH_TOOLS)]

    def register(self, tool: WorkbenchToolDescriptor, *, replace: bool = False) -> WorkbenchToolDescriptor:
        normalized = tool.normalized()
        tools = {item.id: item for item in self.list(visible_only=False)}
        if normalized.id in tools and not replace:
            raise KeyError(f"Tool already registered: {normalized.id}")
        tools[normalized.id] = normalized
        self.state[WORKBENCH_TOOLS_KEY] = [item.to_dict() for item in sorted(tools.values(), key=lambda item: (item.order, item.category, item.id))]
        ApplicationEventBus(self.state).publish("workbench.tool.registered", normalized.to_dict(), source="WorkbenchToolRegistry")
        return normalized

    def get(self, tool_id: str) -> WorkbenchToolDescriptor:
        clean_id = str(tool_id or "").strip()
        for tool in self.list(visible_only=False):
            if tool.id == clean_id:
                return tool
        raise KeyError(f"Unknown Workbench tool: {clean_id}")

    def list(self, *, category: str | None = None, visible_only: bool = True, enabled_only: bool = False) -> tuple[WorkbenchToolDescriptor, ...]:
        tools = tuple(WorkbenchToolDescriptor.from_dict(item) for item in _tool_tuple(self.state.get(WORKBENCH_TOOLS_KEY)))
        if category is not None:
            tools = tuple(tool for tool in tools if tool.category == category)
        if visible_only:
            tools = tuple(tool for tool in tools if tool.visible)
        if enabled_only:
            tools = tuple(tool for tool in tools if tool.enabled)
        return tuple(sorted(tools, key=lambda item: (item.order, item.category, item.id)))


class WorkbenchToolManager:
    """Activation pipeline for workbench tools."""

    def __init__(self, state: MutableMapping[str, Any], registry: WorkbenchToolRegistry | None = None) -> None:
        self.state = state
        self.registry = registry or WorkbenchToolRegistry(state)
        self.event_bus = ApplicationEventBus(state)

    def active_tool_id(self) -> str:
        requested = str(self.state.get(WORKBENCH_ACTIVE_TOOL_KEY, "") or "").strip()
        available = {tool.id for tool in self.registry.list(enabled_only=True)}
        if requested in available:
            return requested
        fallback = next(iter(self.registry.list(enabled_only=True)), None)
        return fallback.id if fallback else ""

    def open_tool_ids(self) -> tuple[str, ...]:
        available = {tool.id for tool in self.registry.list(enabled_only=True)}
        opened = [tool_id for tool_id in _string_list(self.state.get(WORKBENCH_OPEN_TOOLS_KEY)) if tool_id in available]
        active = self.active_tool_id()
        if active and active not in opened:
            opened.append(active)
        order = [tool_id for tool_id in _string_list(self.state.get(WORKBENCH_TOOL_ORDER_KEY)) if tool_id in opened]
        ordered = order + [tool_id for tool_id in opened if tool_id not in order]
        return tuple(ordered)

    def activate(self, tool_id: str, metadata: dict[str, Any] | None = None) -> WorkbenchToolDescriptor:
        tool = self.registry.get(tool_id)
        if not tool.enabled:
            raise KeyError(f"Workbench tool is disabled: {tool.id}")
        previous = str(self.state.get(WORKBENCH_ACTIVE_TOOL_KEY, "") or "")
        opened = list(self.open_tool_ids())
        if tool.id not in opened:
            opened.append(tool.id)
        self.state[WORKBENCH_ACTIVE_TOOL_KEY] = tool.id
        self.state[WORKBENCH_OPEN_TOOLS_KEY] = opened
        self.state[WORKBENCH_TOOL_ORDER_KEY] = opened
        self.event_bus.publish(
            "workbench.tool.activated",
            {"tool_id": tool.id, "previous_tool_id": previous, "metadata": dict(metadata or {})},
            source="WorkbenchToolManager",
        )
        if previous != tool.id:
            self.event_bus.publish(
                "workbench.active_tool.changed",
                {"active_tool_id": tool.id, "previous_tool_id": previous},
                source="WorkbenchToolManager",
            )
        return tool

    def deactivate(self, tool_id: str, *, fallback: str | None = None) -> dict[str, Any]:
        tool = self.registry.get(tool_id)
        opened = [item for item in self.open_tool_ids() if item != tool.id]
        active = str(self.state.get(WORKBENCH_ACTIVE_TOOL_KEY, "") or "")
        next_active = active
        if active == tool.id:
            if fallback:
                next_active = self.registry.get(fallback).id
                if next_active not in opened:
                    opened.append(next_active)
            else:
                next_active = opened[-1] if opened else ""
        self.state[WORKBENCH_OPEN_TOOLS_KEY] = opened
        self.state[WORKBENCH_TOOL_ORDER_KEY] = opened
        self.state[WORKBENCH_ACTIVE_TOOL_KEY] = next_active
        payload = {"tool_id": tool.id, "active_tool_id": next_active, "open_tools": list(opened)}
        self.event_bus.publish("workbench.tool.deactivated", payload, source="WorkbenchToolManager")
        if active != next_active:
            self.event_bus.publish(
                "workbench.active_tool.changed",
                {"active_tool_id": next_active, "previous_tool_id": active},
                source="WorkbenchToolManager",
            )
        return payload

    def summary(self) -> dict[str, Any]:
        active = self.active_tool_id()
        tools = self.registry.list()
        open_ids = self.open_tool_ids()
        return {
            "active_tool_id": active,
            "open_tool_ids": list(open_ids),
            "tools": [tool.to_dict() for tool in tools],
            "available_tool_ids": [tool.id for tool in tools if tool.enabled and tool.visible],
        }


def register_workbench_tool_commands(
    state: MutableMapping[str, Any],
    registry: WorkbenchCommandRegistry | None = None,
    tool_manager: WorkbenchToolManager | None = None,
) -> WorkbenchCommandRegistry:
    """Register tool activation commands in the Workbench command framework."""

    command_registry = registry or WorkbenchCommandRegistry(state)
    manager = tool_manager or WorkbenchToolManager(state)

    def _activate(payload: dict[str, Any]) -> dict[str, Any]:
        tool_id = str(payload.get("tool_id") or payload.get("id") or "").strip()
        tool = manager.activate(tool_id, metadata=dict(payload.get("metadata", {}) or {}))
        return tool.to_dict()

    def _deactivate(payload: dict[str, Any]) -> dict[str, Any]:
        tool_id = str(payload.get("tool_id") or payload.get("id") or "").strip()
        fallback = payload.get("fallback")
        return manager.deactivate(tool_id, fallback=str(fallback) if fallback else None)

    command_registry.register(
        WorkbenchCommand(
            WORKBENCH_ACTIVATE_TOOL_COMMAND_ID,
            "Активировать инструмент",
            "workbench",
            "Открыть или сфокусировать инструмент Workbench через command layer.",
            payload={},
        ),
        _activate,
        replace=True,
    )
    command_registry.register(
        WorkbenchCommand(
            WORKBENCH_DEACTIVATE_TOOL_COMMAND_ID,
            "Деактивировать инструмент",
            "workbench",
            "Закрыть инструмент Workbench через command layer.",
            payload={},
        ),
        _deactivate,
        replace=True,
    )
    return command_registry
