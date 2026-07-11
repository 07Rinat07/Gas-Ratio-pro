"""Single navigation model for the Modern Workbench.

The router binds shell navigation entries to existing Workbench tools.  It does
not parse files, calculate engineering values or render UI.  Controllers use it
to keep the selected navigation section and active tool synchronized.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class WorkbenchModuleRoute:
    """One application-level route from navigation to an existing tool."""

    navigation_id: str
    workspace: str
    tool_id: str
    primary: bool = False
    metadata: dict[str, Any] | None = None

    def normalized(self) -> "WorkbenchModuleRoute":
        navigation_id = str(self.navigation_id or "").strip()
        workspace = str(self.workspace or "").strip()
        tool_id = str(self.tool_id or "").strip()
        if not navigation_id:
            raise ValueError("Workbench module navigation id must not be empty.")
        if not workspace:
            raise ValueError("Workbench module workspace must not be empty.")
        if not tool_id:
            raise ValueError("Workbench module tool id must not be empty.")
        return WorkbenchModuleRoute(
            navigation_id=navigation_id,
            workspace=workspace,
            tool_id=tool_id,
            primary=bool(self.primary),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        route = self.normalized()
        return {
            "navigation_id": route.navigation_id,
            "workspace": route.workspace,
            "tool_id": route.tool_id,
            "primary": route.primary,
            "metadata": dict(route.metadata or {}),
        }


DEFAULT_WORKBENCH_MODULE_ROUTES: tuple[WorkbenchModuleRoute, ...] = (
    WorkbenchModuleRoute("nav.dashboard", "dashboard", "tool.workspace_explorer"),
    WorkbenchModuleRoute(
        "nav.las_workspace",
        "las_workspace",
        "tool.las_viewer",
        primary=True,
        metadata={"module": "las_viewer", "service_contract": "LasViewerToolViewProvider"},
    ),
    WorkbenchModuleRoute("nav.interpretation", "interpretation", "tool.gas_ratio_analysis"),
    WorkbenchModuleRoute("nav.reports", "reports", "tool.report_preview"),
    WorkbenchModuleRoute("nav.exports", "exports", "tool.export"),
)


class WorkbenchNavigationRouter:
    """Resolve navigation and tool ids through one deterministic route table."""

    def __init__(self, routes: Iterable[WorkbenchModuleRoute] | None = None) -> None:
        normalized = tuple(route.normalized() for route in (routes or DEFAULT_WORKBENCH_MODULE_ROUTES))
        navigation_ids = [route.navigation_id for route in normalized]
        if len(navigation_ids) != len(set(navigation_ids)):
            raise ValueError("Workbench module routes contain duplicate navigation ids.")
        self._routes = normalized

    def routes(self) -> tuple[WorkbenchModuleRoute, ...]:
        return self._routes

    def by_navigation(self, navigation_id: str) -> WorkbenchModuleRoute:
        clean_id = str(navigation_id or "").strip()
        for route in self._routes:
            if route.navigation_id == clean_id:
                return route
        raise KeyError(f"Unknown Workbench navigation route: {clean_id}")

    def by_tool(self, tool_id: str) -> WorkbenchModuleRoute:
        clean_id = str(tool_id or "").strip()
        for route in self._routes:
            if route.tool_id == clean_id:
                return route
        raise KeyError(f"Unknown Workbench tool route: {clean_id}")

    def payload(self) -> list[dict[str, Any]]:
        return [route.to_dict() for route in self._routes]
