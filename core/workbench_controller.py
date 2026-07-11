"""Controller layer for the Modern Workbench.

The controller is the coordination boundary between renderer adapters,
Workbench state, the command framework and workspace/session data.  UI code
should use this object instead of reading or mutating Workbench internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping

from core.command_framework import CommandExecutionResult, WorkbenchCommandRegistry
from core.workbench_context import WorkbenchSelection, WorkbenchSelectionService, WorkspaceContext
from core.workbench_lifecycle import WorkbenchLifecycleManager, WorkbenchLifecycleResult
from core.workbench_navigation import WorkbenchNavigationRouter
from core.workbench_dispatcher import WorkbenchDispatchStep, WorkbenchShellDispatchResult, WorkbenchShellDispatcher
from core.workbench_tools import (
    WORKBENCH_ACTIVATE_TOOL_COMMAND_ID,
    WorkbenchToolDescriptor,
    WorkbenchToolManager,
)
from core.workbench_tool_views import WorkbenchToolViewService
from core.workbench_tool_actions import (
    WORKBENCH_EXPORT_REPORT_BUNDLE_COMMAND_ID,
    WORKBENCH_OPEN_LAS_COMMAND_ID,
    WORKBENCH_REFRESH_REPORT_PREVIEW_COMMAND_ID,
    WORKBENCH_RUN_GAS_RATIO_ANALYSIS_COMMAND_ID,
)
from core.workbench_las_primary_module import (
    LAS_PRIMARY_ACTIVATE, LAS_PRIMARY_ZOOM, LAS_PRIMARY_PAN, LAS_PRIMARY_FIT,
    LAS_PRIMARY_RESET, LAS_PRIMARY_CURSOR, LAS_PRIMARY_SELECTION, LAS_PRIMARY_EXPORT,
)
from core.workbench_shell import (
    WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID,
    WORKBENCH_OPEN_DOCK_PANE_COMMAND_ID,
    WORKBENCH_CLOSE_DOCK_PANE_COMMAND_ID,
    WORKBENCH_COLLAPSE_DOCK_PANE_COMMAND_ID,
    WORKBENCH_RESTORE_DOCK_PANE_COMMAND_ID,
    WORKBENCH_SELECT_NAVIGATION_COMMAND_ID,
    WorkbenchRendererContract,
    WorkbenchShellBuilder,
    WorkbenchShellModel,
    build_workbench_renderer_contract,
)


@dataclass(frozen=True, slots=True)
class WorkbenchControllerResult:
    """Result returned by controller-managed Workbench interactions."""

    command_result: CommandExecutionResult
    shell: WorkbenchShellModel
    contract: WorkbenchRendererContract
    workspace_context: WorkspaceContext | None = None
    tool_views: dict[str, Any] | None = None
    module_routes: list[dict[str, Any]] | None = None
    active_module: dict[str, Any] | None = None
    shell_dispatch: WorkbenchShellDispatchResult | None = None

    def view_model(self) -> dict[str, Any]:
        """Return the renderer-facing payload after the interaction."""

        payload = self.contract.to_dict()
        if self.workspace_context is not None:
            payload["workspace_context"] = self.workspace_context.to_dict()
        if self.tool_views is not None:
            payload["tool_views"] = dict(self.tool_views)
        if self.module_routes is not None:
            payload["module_routes"] = list(self.module_routes)
        if self.active_module is not None:
            payload["active_module"] = dict(self.active_module)
        if self.shell_dispatch is not None:
            payload["shell_event"] = self.shell_dispatch.to_dict()
        return payload


class WorkbenchController:
    """Central coordinator for Workbench rendering and interactions.

    The controller validates navigation and dock requests against the current
    shell model, delegates state changes to the command framework, then rebuilds
    the shell/contract so renderers always receive a fresh view model.
    """

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        renderer: str = "streamlit-modern",
        version: str = "workbench-renderer-contract",
        command_registry: WorkbenchCommandRegistry | None = None,
    ) -> None:
        self.state = state
        self.renderer = str(renderer or "streamlit-modern").strip() or "streamlit-modern"
        self.version = str(version or "workbench-renderer-contract").strip() or "workbench-renderer-contract"
        self.builder = WorkbenchShellBuilder(state, command_registry=command_registry)
        self.navigation_router = WorkbenchNavigationRouter()

    @property
    def command_registry(self) -> WorkbenchCommandRegistry:
        """Expose the command registry for diagnostics and compatibility."""

        return self.builder.command_registry

    def shell(self) -> WorkbenchShellModel:
        """Build the current UI-neutral Workbench shell."""

        return self.builder.build()

    def contract(self) -> WorkbenchRendererContract:
        """Build the current renderer contract."""

        return build_workbench_renderer_contract(self.shell(), renderer=self.renderer, version=self.version)

    def context(self) -> WorkspaceContext:
        """Return the aggregated workspace context for controllers/renderers."""

        return WorkspaceContext.from_state(self.state, self.shell())

    def view_model(self) -> dict[str, Any]:
        """Return a serializable renderer payload for UI adapters."""

        payload = self.contract().to_dict()
        context = self.context()
        payload["workspace_context"] = context.to_dict()
        tool_views = WorkbenchToolViewService(self.state).payload(context)
        payload["tool_views"] = tool_views
        payload["module_routes"] = self.navigation_router.payload()
        payload["active_module"] = self._active_module_payload(payload, tool_views)
        return payload


    def _active_module_payload(self, payload: dict[str, Any], tool_views: dict[str, Any]) -> dict[str, Any]:
        """Return the selected module contract without exposing service objects."""

        navigation_id = str(payload.get("interaction", {}).get("active_navigation_id", "") or "")
        route = self.navigation_router.by_navigation(navigation_id)
        items = tuple(tool_views.get("items", ()) or ())
        tool_view = next((item for item in items if item.get("id") == route.tool_id), {})
        return {
            "route": route.to_dict(),
            "tool": dict(tool_view),
        }

    def _result(
        self,
        command_result: CommandExecutionResult,
        shell_dispatch: WorkbenchShellDispatchResult | None = None,
    ) -> WorkbenchControllerResult:
        """Build a controller result with a fresh shell, contract and tool views."""

        shell = self.shell()
        context = WorkspaceContext.from_state(self.state, shell)
        contract = build_workbench_renderer_contract(shell, renderer=self.renderer, version=self.version)
        tool_views = WorkbenchToolViewService(self.state).payload(context)
        contract_payload = contract.to_dict()
        return WorkbenchControllerResult(
            command_result,
            shell,
            contract,
            context,
            tool_views,
            self.navigation_router.payload(),
            self._active_module_payload(contract_payload, tool_views),
            shell_dispatch,
        )


    def _shell_state_snapshot(self) -> dict[str, Any]:
        """Return the normalized renderer-safe state emitted after a dispatch."""

        shell = self.shell()
        return {
            "active_navigation_id": shell.interaction.active_navigation_id,
            "active_workspace": shell.interaction.active_workspace,
            "active_tool_id": shell.active_tool_id,
            "active_dock_pane_id": shell.interaction.active_dock_pane_id,
            "open_tool_ids": list(shell.open_tool_ids),
        }

    def _dispatch_shell(
        self,
        intent: str,
        steps: tuple[WorkbenchDispatchStep, ...],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> WorkbenchControllerResult:
        dispatcher = WorkbenchShellDispatcher(
            self.state,
            self.command_registry,
            self._shell_state_snapshot,
        )
        dispatch_result = dispatcher.dispatch(intent, steps, metadata=metadata)
        return self._result(dispatch_result.primary_result, dispatch_result)

    def _navigation_ids(self) -> set[str]:
        return {item.id for item in self.shell().navigation if item.visible and item.enabled}

    def _dock_pane_ids(self) -> set[str]:
        return {pane.id for pane in self.shell().dock_layout.panes if pane.opened and not pane.collapsed}

    def _tool_ids(self) -> set[str]:
        return {tool.id for tool in self.shell().tools if tool.visible and tool.enabled}

    def select_navigation(self, navigation_id: str) -> WorkbenchControllerResult:
        """Select a navigation item through the command framework."""

        clean_id = str(navigation_id or "").strip()
        if clean_id not in self._navigation_ids():
            raise KeyError(f"Unknown or unavailable Workbench navigation item: {clean_id}")
        route = self.navigation_router.by_navigation(clean_id)
        steps = [
            WorkbenchDispatchStep(WORKBENCH_SELECT_NAVIGATION_COMMAND_ID, {"navigation_id": clean_id}),
            WorkbenchDispatchStep(
                WORKBENCH_ACTIVATE_TOOL_COMMAND_ID,
                {"tool_id": route.tool_id, "metadata": {"navigation_id": clean_id}},
            ),
        ]
        tool_pane_id = f"dock.{route.tool_id}"
        if tool_pane_id in {pane.id for pane in self.shell().dock_layout.panes}:
            steps.append(WorkbenchDispatchStep(WORKBENCH_OPEN_DOCK_PANE_COMMAND_ID, {"pane_id": tool_pane_id}))
        return self._dispatch_shell(
            "navigation.select",
            tuple(steps),
            metadata={"navigation_id": clean_id, "tool_id": route.tool_id, "pane_id": tool_pane_id},
        )

    def activate_dock_pane(self, pane_id: str) -> WorkbenchControllerResult:
        """Activate a dock pane through the command framework."""

        clean_id = str(pane_id or "").strip()
        if clean_id not in self._dock_pane_ids():
            raise KeyError(f"Unknown or unavailable Workbench dock pane: {clean_id}")
        return self._dispatch_shell(
            "dock.focus",
            (WorkbenchDispatchStep(WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID, {"pane_id": clean_id}),),
            metadata={"pane_id": clean_id},
        )

    def _dispatch_dock_command(self, command_id: str, pane_id: str) -> WorkbenchControllerResult:
        clean_id = str(pane_id or "").strip()
        all_ids = {pane.id for pane in self.shell().dock_layout.panes}
        if clean_id not in all_ids:
            raise KeyError(f"Unknown Workbench dock pane: {clean_id}")
        intent = {
            WORKBENCH_OPEN_DOCK_PANE_COMMAND_ID: "dock.open",
            WORKBENCH_CLOSE_DOCK_PANE_COMMAND_ID: "dock.close",
            WORKBENCH_COLLAPSE_DOCK_PANE_COMMAND_ID: "dock.collapse",
            WORKBENCH_RESTORE_DOCK_PANE_COMMAND_ID: "dock.restore",
        }.get(command_id, "dock.update")
        return self._dispatch_shell(
            intent,
            (WorkbenchDispatchStep(command_id, {"pane_id": clean_id}),),
            metadata={"pane_id": clean_id},
        )

    def open_dock_pane(self, pane_id: str) -> WorkbenchControllerResult:
        return self._dispatch_dock_command(WORKBENCH_OPEN_DOCK_PANE_COMMAND_ID, pane_id)

    def close_dock_pane(self, pane_id: str) -> WorkbenchControllerResult:
        return self._dispatch_dock_command(WORKBENCH_CLOSE_DOCK_PANE_COMMAND_ID, pane_id)

    def collapse_dock_pane(self, pane_id: str) -> WorkbenchControllerResult:
        return self._dispatch_dock_command(WORKBENCH_COLLAPSE_DOCK_PANE_COMMAND_ID, pane_id)

    def restore_dock_pane(self, pane_id: str) -> WorkbenchControllerResult:
        return self._dispatch_dock_command(WORKBENCH_RESTORE_DOCK_PANE_COMMAND_ID, pane_id)

    def tool_manager(self) -> WorkbenchToolManager:
        """Return the Workbench tool manager bound to this controller state."""

        return WorkbenchToolManager(self.state)

    def activate_tool(self, tool_id: str, metadata: dict[str, Any] | None = None) -> WorkbenchControllerResult:
        """Activate a Workbench tool through the command framework."""

        clean_id = str(tool_id or "").strip()
        if clean_id not in self._tool_ids():
            raise KeyError(f"Unknown or unavailable Workbench tool: {clean_id}")
        steps = [
            WorkbenchDispatchStep(
                WORKBENCH_ACTIVATE_TOOL_COMMAND_ID,
                {"tool_id": clean_id, "metadata": dict(metadata or {})},
            )
        ]
        tool_pane_id = f"dock.{clean_id}"
        if tool_pane_id in {pane.id for pane in self.shell().dock_layout.panes}:
            steps.append(WorkbenchDispatchStep(WORKBENCH_OPEN_DOCK_PANE_COMMAND_ID, {"pane_id": tool_pane_id}))
        return self._dispatch_shell(
            "tool.activate",
            tuple(steps),
            metadata={"tool_id": clean_id, "pane_id": tool_pane_id},
        )

    def list_tools(self) -> tuple[WorkbenchToolDescriptor, ...]:
        """List visible Workbench tool descriptors."""

        return self.shell().tools

    def select_object(self, target: str, object_id: str, metadata: dict[str, Any] | None = None) -> WorkbenchSelection:
        """Change Workbench object selection through the selection service."""

        return WorkbenchSelectionService(self.state).select(target, object_id, metadata)

    def clear_selection(self, reason: str = "selection_cleared") -> WorkbenchSelection:
        """Clear Workbench object selection through the selection service."""

        return WorkbenchSelectionService(self.state).clear(reason)

    def lifecycle(self) -> WorkbenchLifecycleManager:
        """Return the lifecycle manager bound to this controller."""

        return WorkbenchLifecycleManager(self.state, controller=self)

    def initialize(self) -> WorkbenchLifecycleResult:
        """Initialize Workbench lifecycle through the controller boundary."""

        return self.lifecycle().initialize()

    def open_workspace(self) -> WorkbenchLifecycleResult:
        """Open the current lightweight workspace through the lifecycle manager."""

        return self.lifecycle().open_workspace()

    def close_workspace(self, *, save: bool = False) -> WorkbenchLifecycleResult:
        """Close the current lightweight workspace through the lifecycle manager."""

        return self.lifecycle().close_workspace(save=save)

    def dispatch_renderer_action(self, action_id: str, payload: dict[str, Any] | None = None) -> WorkbenchControllerResult:
        """Execute a renderer action using controller-level validation."""

        clean_action_id = str(action_id or "").strip()
        clean_payload = dict(payload or {})
        if clean_action_id == "action.select_navigation":
            return self.select_navigation(str(clean_payload.get("navigation_id") or clean_payload.get("id") or ""))
        if clean_action_id == "action.activate_dock_pane":
            return self.activate_dock_pane(str(clean_payload.get("pane_id") or clean_payload.get("id") or ""))
        if clean_action_id == "action.open_dock_pane":
            return self.open_dock_pane(str(clean_payload.get("pane_id") or clean_payload.get("id") or ""))
        if clean_action_id == "action.close_dock_pane":
            return self.close_dock_pane(str(clean_payload.get("pane_id") or clean_payload.get("id") or ""))
        if clean_action_id == "action.collapse_dock_pane":
            return self.collapse_dock_pane(str(clean_payload.get("pane_id") or clean_payload.get("id") or ""))
        if clean_action_id == "action.restore_dock_pane":
            return self.restore_dock_pane(str(clean_payload.get("pane_id") or clean_payload.get("id") or ""))
        if clean_action_id == "action.activate_tool":
            return self.activate_tool(str(clean_payload.get("tool_id") or clean_payload.get("id") or ""), metadata=dict(clean_payload.get("metadata", {}) or {}))
        if clean_action_id == "action.open_las":
            result = self.command_registry.execute(WORKBENCH_OPEN_LAS_COMMAND_ID, clean_payload)
            return self._result(result)
        if clean_action_id == "action.run_gas_ratio_analysis":
            result = self.command_registry.execute(WORKBENCH_RUN_GAS_RATIO_ANALYSIS_COMMAND_ID, clean_payload)
            return self._result(result)
        if clean_action_id == "action.refresh_report_preview":
            result = self.command_registry.execute(WORKBENCH_REFRESH_REPORT_PREVIEW_COMMAND_ID, clean_payload)
            return self._result(result)
        if clean_action_id == "action.export_report_bundle":
            result = self.command_registry.execute(WORKBENCH_EXPORT_REPORT_BUNDLE_COMMAND_ID, clean_payload)
            return self._result(result)
        las_actions = {
            "action.las_primary_activate": LAS_PRIMARY_ACTIVATE,
            "action.las_primary_zoom": LAS_PRIMARY_ZOOM,
            "action.las_primary_pan": LAS_PRIMARY_PAN,
            "action.las_primary_fit": LAS_PRIMARY_FIT,
            "action.las_primary_reset": LAS_PRIMARY_RESET,
            "action.las_primary_cursor": LAS_PRIMARY_CURSOR,
            "action.las_primary_selection": LAS_PRIMARY_SELECTION,
            "action.las_primary_export": LAS_PRIMARY_EXPORT,
        }
        if clean_action_id in las_actions:
            result = self.command_registry.execute(las_actions[clean_action_id], clean_payload)
            return self._result(result)
        available = set(self.contract().action_ids())
        if clean_action_id not in available:
            raise KeyError(f"Unknown or disabled renderer action: {clean_action_id}")
        raise KeyError(f"Renderer action has no controller handler: {clean_action_id}")


def build_workbench_controller(
    state: MutableMapping[str, Any],
    *,
    renderer: str = "streamlit-modern",
    version: str = "workbench-renderer-contract",
) -> WorkbenchController:
    """Factory used by UI adapters and tests."""

    return WorkbenchController(state, renderer=renderer, version=version)
