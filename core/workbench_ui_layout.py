"""Renderer-neutral production layout contract for Modern Workbench."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class WorkbenchUILayoutContract:
    toolbar: tuple[dict[str, Any], ...]
    project_tree: tuple[dict[str, Any], ...]
    workspace: dict[str, Any]
    properties: tuple[dict[str, Any], ...]
    status_items: tuple[dict[str, Any], ...]
    regions: dict[str, Any] = field(default_factory=dict)
    property_actions: tuple[dict[str, Any], ...] = ()
    property_action_result: dict[str, Any] = field(default_factory=dict)
    show_technical_properties: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "toolbar": [dict(item) for item in self.toolbar],
            "project_tree": [dict(item) for item in self.project_tree],
            "workspace": dict(self.workspace),
            "properties": [dict(item) for item in self.properties],
            "status_items": [dict(item) for item in self.status_items],
            "regions": dict(self.regions),
            "property_actions": [dict(item) for item in self.property_actions],
            "property_action_result": dict(self.property_action_result or {}),
            "show_technical_properties": bool(self.show_technical_properties),
        }


def _value(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text or fallback


def build_workbench_ui_layout(payload: Mapping[str, Any]) -> WorkbenchUILayoutContract:
    """Build a complete engineering-layout payload from existing view contracts."""
    context = dict(payload.get("context", {}) or {})
    status = dict(payload.get("status", {}) or {})
    interaction = dict(payload.get("interaction", {}) or {})
    active_module = dict(payload.get("active_module", {}) or {})
    tool = dict(active_module.get("tool", {}) or {})
    route = dict(active_module.get("route", {}) or {})

    commands = tuple(payload.get("commands", ()) or ())
    module_actions = tuple(tool.get("actions", ()) or ())
    navigation_actions = tuple({
        "ui_id": f"toolbar.navigation.{item.get('id', '')}",
        "id": "action.select_navigation",
        "title": str(item.get("title") or item.get("id") or "Open workspace"),
        "payload": {"navigation_id": str(item.get("id") or "")},
        "enabled": bool(item.get("enabled", True)),
        "category": "project",
    } for item in tuple(payload.get("navigation", ()) or ()) if item.get("id"))
    dock_actions = (
        {"ui_id": "toolbar.dock.project_explorer.collapse", "id": "action.collapse_dock_pane", "title": "Collapse Explorer", "payload": {"pane_id": "dock.project_explorer"}, "enabled": True, "category": "settings"},
        {"ui_id": "toolbar.dock.properties.collapse", "id": "action.collapse_dock_pane", "title": "Collapse Properties", "payload": {"pane_id": "dock.properties"}, "enabled": True, "category": "settings"},
        {"ui_id": "toolbar.dock.project_explorer.restore", "id": "action.restore_dock_pane", "title": "Restore Explorer", "payload": {"pane_id": "dock.project_explorer"}, "enabled": True, "category": "settings"},
        {"ui_id": "toolbar.dock.properties.restore", "id": "action.restore_dock_pane", "title": "Restore Properties", "payload": {"pane_id": "dock.properties"}, "enabled": True, "category": "settings"},
    )
    toolbar_groups = ("file", "project", "data", "las", "interpretation", "report", "settings")
    action_group = {
        "action.open_las": "las", "action.las_primary_activate": "las",
        "action.las_primary_zoom": "las", "action.las_primary_pan": "las",
        "action.las_primary_fit": "las", "action.las_primary_reset": "las",
        "action.las_primary_export": "report", "action.run_gas_ratio_analysis": "interpretation",
        "action.refresh_report_preview": "report", "action.export_report_bundle": "report",
        "action.select_navigation": "project", "action.activate_tool": "project",
        "action.collapse_dock_pane": "settings", "action.restore_dock_pane": "settings",
    }
    all_actions = [dict(item) for item in (*navigation_actions, *dock_actions, *module_actions) if item.get("id")]
    toolbar: list[dict[str, Any]] = []
    for group in toolbar_groups:
        actions = [item for item in all_actions if action_group.get(str(item.get("id")), str(item.get("category", "")).lower()) == group]
        matching = [command for command in commands if str(command.get("group", command.get("category", ""))).lower() == group]
        toolbar.append({
            "id": f"toolbar.{group}", "title": group.title(),
            "command_ids": [str(command.get("id", "")) for command in matching if command.get("id")],
            "actions": actions, "enabled": True,
        })

    project_id = context.get("project_id") or status.get("project_id")
    well_id = context.get("well_id") or status.get("well_id")
    las_id = context.get("las_id") or status.get("las_id")
    providers = dict(payload.get("ui_providers", {}) or {})
    tree = tuple(providers.get("project_tree", ()) or (
        {"id": "tree.project", "title": _value(project_id, "No project open"), "kind": "project", "level": 0, "active": bool(project_id)},
        {"id": "tree.wells", "title": "Wells", "kind": "collection", "level": 1, "count": 1 if well_id else 0},
        {"id": "tree.las", "title": "LAS", "kind": "collection", "level": 1, "count": 1 if las_id else 0},
        {"id": "tree.curves", "title": "Curves", "kind": "collection", "level": 1, "count": 0},
        {"id": "tree.correlation", "title": "Correlation", "kind": "collection", "level": 1, "count": 0},
        {"id": "tree.calculations", "title": "Calculations", "kind": "collection", "level": 1, "count": 0},
        {"id": "tree.reports", "title": "Reports", "kind": "collection", "level": 1, "count": 1 if status.get("active_report") else 0},
        {"id": "tree.exports", "title": "Exports", "kind": "collection", "level": 1, "count": int(status.get("recent_exports_count", 0) or 0)},
    ))

    workspace = {
        "id": "workspace.host",
        "title": tool.get("title") or route.get("title") or "Dashboard",
        "renderer_hint": tool.get("renderer_hint") or "workspace",
        "status": tool.get("status") or "ready",
        "empty_state": tool.get("empty_state") or "Select a module or open a project to begin.",
        "content": dict(tool.get("content", {}) or {}),
        "runtime": dict(providers.get("workspace_runtime", {}) or {}),
        "actions": list(tool.get("actions", ()) or ()),
        "active_tool_id": payload.get("active_tool_id", ""),
        "active_workspace": interaction.get("active_workspace", ""),
    }

    properties = tuple(providers.get("properties", ()) or (
        {"label": "Project", "value": _value(project_id)},
        {"label": "Well", "value": _value(well_id)},
        {"label": "LAS", "value": _value(las_id)},
        {"label": "Module", "value": _value(workspace["title"])},
        {"label": "Renderer", "value": _value(workspace["renderer_hint"])},
        {"label": "State", "value": _value(workspace["status"])},
    ))

    status_items = tuple(providers.get("status_items", ()) or (
        {"label": "Project", "value": _value(project_id)},
        {"label": "Well", "value": _value(well_id)},
        {"label": "LAS", "value": _value(las_id)},
        {"label": "Workspace", "value": _value(interaction.get("active_workspace"))},
        {"label": "Module", "value": _value(workspace["title"])},
        {"label": "Status", "value": "Ready" if status.get("ready") else "Awaiting project"},
    ))
    return WorkbenchUILayoutContract(
        toolbar=tuple(toolbar), project_tree=tree, workspace=workspace,
        properties=properties, status_items=status_items,
        regions={"left": "project_explorer", "center": "workspace_host", "right": "properties", "top": "command_toolbar", "bottom": "status_bar"},
        property_actions=tuple(providers.get("property_actions", ()) or ()),
        property_action_result=dict(providers.get("property_action_result", {}) or {}),
        show_technical_properties=bool(providers.get("show_technical_properties", False)),
    )
