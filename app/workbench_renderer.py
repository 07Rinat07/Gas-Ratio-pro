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
from core.workbench_ui_layout import build_workbench_ui_layout
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
    """Return production Workbench layout CSS."""
    return """
<style>
.block-container { max-width: 100% !important; padding: .65rem .9rem 0 !important; }
.workbench-contract-shell { height: calc(100vh - 1rem); max-width: 100%; overflow: hidden; overflow-x: hidden; display:flex; flex-direction:column; gap:.55rem; color:#e8edf5; }
.workbench-titlebar { display:flex; align-items:center; justify-content:space-between; min-height:42px; padding:0 .35rem; }
.workbench-titlebar h1 { font-size:1.25rem; margin:0; }
.workbench-toolbar { display:flex; flex-wrap:wrap; gap:.4rem; padding:.45rem; border:1px solid #273246; border-radius:.65rem; background:#111722; }
.workbench-toolbar-item { padding:.4rem .7rem; border-radius:.45rem; background:#182235; border:1px solid #30405a; font-size:.82rem; }
.workbench-main { display:grid; grid-template-columns:1fr; gap:.6rem; flex:1; min-height:0; }
.workbench-pane { min-width:0; min-height:0; overflow:auto; border:1px solid #273246; border-radius:.65rem; background:#0f141e; }
.workbench-pane-header { position:sticky; top:0; z-index:2; padding:.65rem .75rem; font-weight:700; background:#151d2a; border-bottom:1px solid #273246; }
.workbench-pane-body { padding:.65rem .75rem; }
.workbench-tree-item { padding:.38rem .45rem; border-radius:.35rem; margin:.12rem 0; display:flex; justify-content:space-between; }
.workbench-tree-item:hover { background:#182235; }
.workbench-workspace { min-height:420px; display:flex; flex-direction:column; }
.workbench-workspace-empty { margin:auto; max-width:34rem; text-align:center; color:#9eabc0; padding:2rem; }
.workbench-property { display:grid; grid-template-columns:minmax(5rem,.8fr) minmax(0,1.2fr); gap:.5rem; padding:.38rem 0; border-bottom:1px solid #202a3b; font-size:.85rem; }
.workbench-property span:first-child { color:#8fa0b8; }
.workbench-statusbar { display:flex; flex-wrap:wrap; gap:.5rem 1.1rem; padding:.4rem .7rem; border:1px solid #273246; border-radius:.5rem; background:#111722; font-size:.76rem; }
.workbench-statusbar strong { color:#8fa0b8; font-weight:500; }
.workbench-contract-shell button { min-height: 44px; white-space:normal; }
.workbench-focus-target:focus-visible { outline:3px solid #4d9fff; outline-offset:2px; }
@media (max-width: 1023px) { .workbench-contract-shell { height:auto; overflow:visible; } .workbench-main { grid-template-columns:1fr; } .workbench-pane { overflow:visible; } }
@media (min-width: 600px) { .workbench-toolbar { gap:.5rem; } }
@media (min-width: 1024px) { .workbench-main { grid-template-columns:minmax(14rem, 18rem) minmax(0, 1fr) minmax(16rem, 20rem); } }
@media (min-width: 1600px) { .workbench-main { grid-template-columns:minmax(16rem,18rem) minmax(0,1fr) minmax(18rem,21rem); } }
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


def _html(text: Any) -> str:
    import html
    return html.escape(str(text if text is not None else ""))


def render_streamlit_workbench_contract(
    contract: WorkbenchRendererContract,
    registry: WorkbenchCommandRegistry,
    st_module: StreamlitLike,
    *,
    view_model: dict[str, Any] | None = None,
) -> tuple[CommandExecutionResult, ...]:
    """Render the complete production Workbench engineering layout."""
    payload = dict(view_model or contract.to_dict())
    executed: list[CommandExecutionResult] = []
    layout = build_workbench_ui_layout(payload).to_dict()

    st_module.markdown(build_workbench_responsive_css(), unsafe_allow_html=True)
    title = "Modern Workbench"
    active_workspace = payload.get("interaction", {}).get("active_workspace") or "dashboard"
    st_module.markdown(
        f"<main class='workbench-contract-shell' aria-label='Modern Workbench'>"
        f"<div class='workbench-titlebar'><h1>{title}</h1><span>Workspace: <b>{_html(active_workspace)}</b></span></div>",
        unsafe_allow_html=True,
    )

    toolbar_html = "".join(
        f"<span class='workbench-toolbar-item' role='group' aria-label='{_html(item['title'])}'>{_html(item['title'])}</span>"
        for item in layout["toolbar"]
    )
    st_module.markdown(f"<nav class='workbench-toolbar' aria-label='Command toolbar'>{toolbar_html}</nav>", unsafe_allow_html=True)

    tree_html = "".join(
        f"<div class='workbench-tree-item' style='padding-left:{.45 + .8 * int(item.get('level', 0))}rem'>"
        f"<span>{_html(item['title'])}</span><small>{_html(item.get('count', ''))}</small></div>"
        for item in layout["project_tree"]
    )
    workspace = layout["workspace"]
    cards = workspace.get("content", {}).get("summary_cards", [])
    cards_html = "".join(f"<div class='workbench-property'><span>{_html(card.get('title'))}</span><b>{_html(card.get('value'))}</b></div>" for card in cards)
    center_html = cards_html or f"<div class='workbench-workspace-empty'><h3>{_html(workspace['title'])}</h3><p>{_html(workspace['empty_state'])}</p></div>"
    props_html = "".join(f"<div class='workbench-property'><span>{_html(item['label'])}</span><b>{_html(item['value'])}</b></div>" for item in layout["properties"] )
    st_module.markdown(
        "<section class='workbench-main'>"
        f"<aside class='workbench-pane' aria-label='Project Explorer'><div class='workbench-pane-header'>Project Explorer</div><div class='workbench-pane-body'>{tree_html}</div></aside>"
        f"<section class='workbench-pane workbench-workspace' aria-label='Workspace host'><div class='workbench-pane-header'>{_html(workspace['title'])}</div><div class='workbench-pane-body'>{center_html}</div></section>"
        f"<aside class='workbench-pane' aria-label='Properties'><div class='workbench-pane-header'>Properties</div><div class='workbench-pane-body'>{props_html}</div></aside>"
        "</section>", unsafe_allow_html=True,
    )

    # Command-backed navigation stays outside generated HTML because Streamlit
    # buttons are the accessible execution surface.
    active_navigation_id = payload.get("interaction", {}).get("active_navigation_id", "")
    for item in payload.get("navigation", []):
        prefix = "● " if item.get("id") == active_navigation_id else "○ "
        if st_module.button(prefix + str(item.get("title", item.get("id", ""))), key=_navigation_button_key(item.get("id", ""))):
            executed.append(dispatch_workbench_renderer_action(contract, registry, "action.select_navigation", {"navigation_id": item.get("id", "")}))

    # Keep dock focus controls command-backed for keyboard users and adapters.
    active_pane_id = payload.get("interaction", {}).get("active_dock_pane_id", "")
    panel_titles = {panel.get("id"): panel.get("title", panel.get("id")) for panel in payload.get("panels", [])}
    pane_ids = [pane_id for region in payload.get("dock_regions", {}).values() for pane_id in region]
    for pane_id in pane_ids:
        panel_id = str(pane_id).replace("dock.", "")
        prefix = "● " if pane_id == active_pane_id else "○ "
        if st_module.button(prefix + str(panel_titles.get(panel_id, pane_id)), key=_dock_button_key(pane_id)):
            executed.append(dispatch_workbench_renderer_action(contract, registry, "action.activate_dock_pane", {"pane_id": pane_id}))

    status_html = "".join(f"<span><strong>{_html(item['label'])}:</strong> {_html(item['value'])}</span>" for item in layout["status_items"] )
    st_module.markdown(f"<footer class='workbench-statusbar' aria-label='Status bar'>{status_html}</footer></main>", unsafe_allow_html=True)
    return tuple(executed)

def render_streamlit_workbench(state: MutableMapping[str, Any], st_module: StreamlitLike) -> tuple[CommandExecutionResult, ...]:
    """Build and render the first Modern Workbench Streamlit adapter."""

    adapter = build_streamlit_workbench_adapter(state)
    return render_streamlit_workbench_contract(adapter.contract, adapter.registry, st_module, view_model=adapter.payload())
