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
from core.workbench_shell import (
    WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID,
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

    def view_model(self) -> dict[str, Any]:
        """Return the renderer-facing payload after the interaction."""

        return self.contract.to_dict()


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
        payload["workspace_context"] = self.context().to_dict()
        return payload

    def _navigation_ids(self) -> set[str]:
        return {item.id for item in self.shell().navigation if item.visible and item.enabled}

    def _dock_pane_ids(self) -> set[str]:
        return {pane.id for pane in self.shell().dock_layout.panes if not pane.collapsed}

    def select_navigation(self, navigation_id: str) -> WorkbenchControllerResult:
        """Select a navigation item through the command framework."""

        clean_id = str(navigation_id or "").strip()
        if clean_id not in self._navigation_ids():
            raise KeyError(f"Unknown or unavailable Workbench navigation item: {clean_id}")
        result = self.command_registry.execute(
            WORKBENCH_SELECT_NAVIGATION_COMMAND_ID,
            {"navigation_id": clean_id},
        )
        shell = self.shell()
        return WorkbenchControllerResult(result, shell, build_workbench_renderer_contract(shell, renderer=self.renderer, version=self.version))

    def activate_dock_pane(self, pane_id: str) -> WorkbenchControllerResult:
        """Activate a dock pane through the command framework."""

        clean_id = str(pane_id or "").strip()
        if clean_id not in self._dock_pane_ids():
            raise KeyError(f"Unknown or unavailable Workbench dock pane: {clean_id}")
        result = self.command_registry.execute(
            WORKBENCH_ACTIVATE_DOCK_PANE_COMMAND_ID,
            {"pane_id": clean_id},
        )
        shell = self.shell()
        return WorkbenchControllerResult(result, shell, build_workbench_renderer_contract(shell, renderer=self.renderer, version=self.version))

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
