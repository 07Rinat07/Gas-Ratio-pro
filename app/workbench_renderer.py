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
from core.workbench_controller import WorkbenchController, build_workbench_controller
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
    controller: WorkbenchController | None = None

    def payload(self) -> dict[str, Any]:
        """Return the serializable renderer view model for diagnostics/tests."""

        if self.controller is not None:
            return self.controller.view_model()
        return self.contract.to_dict()


def build_streamlit_workbench_adapter(state: MutableMapping[str, Any]) -> StreamlitWorkbenchAdapter:
    """Build a Streamlit Workbench adapter from application/session state."""

    controller = build_workbench_controller(
        state,
        renderer=WORKBENCH_RENDERER_NAME,
        version=WORKBENCH_RENDERER_CONTRACT_VERSION,
    )
    contract = controller.contract()
    return StreamlitWorkbenchAdapter(
        contract=contract,
        registry=controller.command_registry,
        controller=controller,
    )




def build_workbench_responsive_css() -> str:
    """Return the audited responsive shell CSS used by the Streamlit adapter."""

    return """
<style>
.workbench-contract-shell { max-width: 100%; overflow-x: hidden; }
.workbench-contract-shell button { min-height: 44px; white-space: normal; }
.workbench-contract-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: .75rem; }
.workbench-focus-target:focus-visible { outline: 3px solid #0B63CE; outline-offset: 2px; }
@media (min-width: 600px) { .workbench-contract-grid { grid-template-columns: minmax(0, 1fr); } }
@media (min-width: 1024px) { .workbench-contract-grid { grid-template-columns: minmax(14rem, .6fr) minmax(0, 1.4fr); } }
@media (min-width: 1600px) { .workbench-contract-grid { grid-template-columns: minmax(16rem, .55fr) minmax(0, 1.45fr) minmax(18rem, .65fr); } }
</style>
""".strip()


def _accessibility_by_target(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("target", "")): item
        for item in payload.get("accessibility", {}).get("elements", [])
        if item.get("target")
    }


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

    # Keep the public helper backward compatible, but route known renderer
    # actions through the controller so UI adapters never mutate or validate
    # Workbench state themselves.
    controller = WorkbenchController(
        registry.state,
        renderer=contract.renderer,
        version=contract.version,
        command_registry=registry,
    )
    return controller.dispatch_renderer_action(clean_action_id, dict(payload or {})).command_result


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
    accessibility = _accessibility_by_target(payload)

    st_module.markdown(build_workbench_responsive_css(), unsafe_allow_html=True)
    st_module.markdown("<main class='workbench-contract-shell' aria-label='Modern Workbench'>", unsafe_allow_html=True)
    st_module.markdown("### Modern Workbench")
    status = payload.get("status", {})
    active_workspace = payload.get("interaction", {}).get("active_workspace") or "dashboard"
    st_module.markdown(f"Workspace: `{active_workspace}`")
    if status.get("project_id"):
        st_module.markdown(f"Project: `{status['project_id']}`")

    active_navigation_id = payload.get("interaction", {}).get("active_navigation_id", "")
    for item in payload.get("navigation", []):
        label_prefix = "● " if item.get("id") == active_navigation_id else "○ "
        item_accessibility = accessibility.get(str(item.get("id", "")), {})
        if st_module.button(
            label_prefix + str(item.get("title", item.get("id", ""))),
            key=_navigation_button_key(item.get("id", "")),
            help=item_accessibility.get("description", ""),
        ):
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
        pane_accessibility = accessibility.get(str(pane_id), {})
        if st_module.button(
            label_prefix + str(title),
            key=_dock_button_key(pane_id),
            help=pane_accessibility.get("description", ""),
        ):
            executed.append(
                dispatch_workbench_renderer_action(
                    contract,
                    registry,
                    "action.activate_dock_pane",
                    {"pane_id": pane_id},
                )
            )

    st_module.markdown("</main>", unsafe_allow_html=True)
    return tuple(executed)


def render_streamlit_workbench(state: MutableMapping[str, Any], st_module: StreamlitLike) -> tuple[CommandExecutionResult, ...]:
    """Build and render the first Modern Workbench Streamlit adapter."""

    adapter = build_streamlit_workbench_adapter(state)
    return render_streamlit_workbench_contract(adapter.contract, adapter.registry, st_module)
