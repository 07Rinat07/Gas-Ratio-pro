"""Streamlit adapter for the Modern Workbench renderer contract.

The adapter is intentionally thin: it renders the already prepared
``WorkbenchRendererContract`` payload and dispatches action command ids through
``WorkbenchCommandRegistry``.  It does not calculate interpretations, mutate
workspace data directly, perform exports or persist domain objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping, Protocol

from core.command_framework import CommandExecutionResult, WorkbenchCommandRegistry
from core.workbench_shell import (
    WorkbenchRendererContract,
    WorkbenchShellBuilder,
    build_workbench_renderer_contract,
)

WORKBENCH_RENDERER_NAME = "streamlit-modern"
WORKBENCH_RENDERER_CONTRACT_VERSION = "workbench-renderer-contract"


class StreamlitLike(Protocol):
    """Minimal Streamlit surface used by this adapter.

    Tests can pass a small fake object implementing these methods.  The real
    ``streamlit`` module also satisfies this protocol for the calls below.
    """

    def markdown(self, body: str, *args: Any, **kwargs: Any) -> Any: ...
    def button(self, label: str, *args: Any, **kwargs: Any) -> bool: ...


@dataclass(frozen=True, slots=True)
class StreamlitWorkbenchAdapter:
    """Ready-to-render Workbench adapter bundle.

    ``contract`` is the UI payload.  ``registry`` is the only allowed execution
    path for UI actions.  A Streamlit page should pass these two objects into the
    renderer and never update Workbench session keys manually.
    """

    contract: WorkbenchRendererContract
    registry: WorkbenchCommandRegistry

    def payload(self) -> dict[str, Any]:
        """Return the serializable contract payload for diagnostics/tests."""

        return self.contract.to_dict()


def build_streamlit_workbench_adapter(state: MutableMapping[str, Any]) -> StreamlitWorkbenchAdapter:
    """Build a Streamlit Workbench adapter from application/session state."""

    builder = WorkbenchShellBuilder(state)
    shell = builder.build()
    contract = build_workbench_renderer_contract(
        shell,
        renderer=WORKBENCH_RENDERER_NAME,
        version=WORKBENCH_RENDERER_CONTRACT_VERSION,
    )
    return StreamlitWorkbenchAdapter(contract=contract, registry=builder.command_registry)


def _contract_action_map(contract: WorkbenchRendererContract) -> dict[str, dict[str, Any]]:
    return {action["id"]: action for action in contract.to_dict()["actions"] if action.get("enabled", True)}


def dispatch_workbench_renderer_action(
    contract: WorkbenchRendererContract,
    registry: WorkbenchCommandRegistry,
    action_id: str,
    payload: dict[str, Any] | None = None,
) -> CommandExecutionResult:
    """Execute a renderer action through its command-backed contract entry.

    The renderer is not allowed to know how Workbench state is stored.  It only
    submits an action id and a small payload; this helper resolves the command id
    from the contract and delegates execution to the command registry.
    """

    clean_action_id = str(action_id or "").strip()
    actions = _contract_action_map(contract)
    if clean_action_id not in actions:
        raise KeyError(f"Unknown or disabled renderer action: {clean_action_id}")
    command_id = str(actions[clean_action_id]["command_id"])
    return registry.execute(command_id, dict(payload or {}))


def _navigation_button_key(item_id: str) -> str:
    return "workbench_nav_" + str(item_id).replace(".", "_").replace(" ", "_")


def _dock_button_key(pane_id: str) -> str:
    return "workbench_dock_" + str(pane_id).replace(".", "_").replace(" ", "_")


def render_streamlit_workbench_contract(
    contract: WorkbenchRendererContract,
    registry: WorkbenchCommandRegistry,
    st_module: StreamlitLike,
) -> tuple[CommandExecutionResult, ...]:
    """Render the Modern Workbench contract with a minimal Streamlit surface.

    The function returns command execution results produced by clicked controls.
    In a real Streamlit run the caller can trigger a rerun after a successful
    result; tests can assert that button clicks are translated to command calls.
    """

    payload = contract.to_dict()
    executed: list[CommandExecutionResult] = []

    st_module.markdown("### Modern Workbench")
    status = payload.get("status", {})
    active_workspace = payload.get("interaction", {}).get("active_workspace") or "dashboard"
    st_module.markdown(f"Workspace: `{active_workspace}`")
    if status.get("project_id"):
        st_module.markdown(f"Project: `{status['project_id']}`")

    active_navigation_id = payload.get("interaction", {}).get("active_navigation_id", "")
    for item in payload.get("navigation", []):
        label_prefix = "● " if item.get("id") == active_navigation_id else "○ "
        if st_module.button(label_prefix + str(item.get("title", item.get("id", ""))), key=_navigation_button_key(item.get("id", ""))):
            executed.append(
                dispatch_workbench_renderer_action(
                    contract,
                    registry,
                    "action.select_navigation",
                    {"navigation_id": item.get("id", "")},
                )
            )

    st_module.markdown("#### Dock panels")
    active_pane_id = payload.get("interaction", {}).get("active_dock_pane_id", "")
    panel_titles = {panel.get("id"): panel.get("title", panel.get("id")) for panel in payload.get("panels", [])}
    pane_ids = [pane_id for region in payload.get("dock_regions", {}).values() for pane_id in region]
    for pane_id in pane_ids:
        panel_id = str(pane_id).replace("dock.", "")
        title = panel_titles.get(panel_id, pane_id)
        label_prefix = "● " if pane_id == active_pane_id else "○ "
        if st_module.button(label_prefix + str(title), key=_dock_button_key(pane_id)):
            executed.append(
                dispatch_workbench_renderer_action(
                    contract,
                    registry,
                    "action.activate_dock_pane",
                    {"pane_id": pane_id},
                )
            )

    return tuple(executed)


def render_streamlit_workbench(state: MutableMapping[str, Any], st_module: StreamlitLike) -> tuple[CommandExecutionResult, ...]:
    """Build and render the first Modern Workbench Streamlit adapter."""

    adapter = build_streamlit_workbench_adapter(state)
    return render_streamlit_workbench_contract(adapter.contract, adapter.registry, st_module)
