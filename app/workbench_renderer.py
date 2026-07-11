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
from core.build_info import runtime_build_info
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
    """Return the professional Workbench visual system for Streamlit."""
    return """
<style>
:root { --wb-bg:#0b1018; --wb-surface:#111925; --wb-surface-2:#162131; --wb-line:#2b3a50; --wb-text:#edf3fb; --wb-muted:#91a2b8; --wb-accent:#3f8cff; --wb-success:#38c77a; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:var(--wb-bg) !important; color:var(--wb-text); overflow-x: hidden; }
.block-container { max-width:100% !important; padding:.35rem .55rem .2rem !important; }
[data-testid="stHeader"] { height:2.2rem; background:rgba(11,16,24,.92); }
[data-testid="stToolbar"] { top:.15rem; }
.workbench-titlebar { display:flex; align-items:center; justify-content:space-between; min-height:48px; padding:.25rem .55rem; border-bottom:1px solid var(--wb-line); background:linear-gradient(180deg,#121c2a,#0e151f); }
.workbench-brand { display:flex; gap:.65rem; align-items:center; }
.workbench-logo { width:28px; height:28px; display:grid; place-items:center; border-radius:7px; color:white; background:linear-gradient(135deg,#2f78ff,#18b7d8); font-size:1.05rem; box-shadow:0 0 18px rgba(63,140,255,.25); }
.workbench-titlebar h1 { font-size:1.28rem; line-height:1.2; margin:0; letter-spacing:.01em; }
.workbench-subtitle { color:var(--wb-muted); font-size:.75rem; }
.workbench-build { color:var(--wb-muted); font-size:.72rem; text-align:right; }
.workbench-menu { display:flex; align-items:center; gap:.15rem; min-height:38px; padding:0 .4rem; border-bottom:1px solid var(--wb-line); background:#0f1722; overflow-x:auto; }
.workbench-menu-item { padding:.55rem .82rem; border-bottom:2px solid transparent; color:#c9d5e5; font-weight:600; font-size:.82rem; white-space:nowrap; }
.workbench-menu-item.active { color:white; border-bottom-color:var(--wb-accent); background:rgba(63,140,255,.08); }
.workbench-ribbon { padding:.45rem .5rem .5rem; border-bottom:1px solid var(--wb-line); background:linear-gradient(180deg,#121b28,#0e151f); }
.workbench-ribbon-label { color:var(--wb-muted); text-transform:uppercase; letter-spacing:.08em; font-size:.64rem; margin:.1rem 0 .25rem; }
.workbench-runtime-source { display:none; }
[data-testid="stHorizontalBlock"] { gap:.55rem; }
div[data-testid="stButton"] > button { min-height: 44px; border-radius:6px; border:1px solid #344760; background:linear-gradient(180deg,#1b2a3d,#142031); color:#f1f6fd; font-size:.82rem; font-weight:600; padding:.45rem .65rem; box-shadow:none; }
div[data-testid="stButton"] > button:hover { border-color:#4e8be8; background:linear-gradient(180deg,#233752,#182943); color:white; }
div[data-testid="stButton"] > button:focus-visible { outline:3px solid rgba(77,159,255,.75); outline-offset:2px; }
.workbench-pane-title { display:flex; align-items:center; justify-content:space-between; min-height:36px; padding:.45rem .65rem; margin-bottom:.4rem; border-bottom:1px solid var(--wb-line); background:#131d2a; font-weight:700; font-size:.9rem; }
.workbench-tree-item { padding:.43rem .5rem; border-radius:5px; margin:.08rem 0; display:flex; align-items:center; justify-content:space-between; font-size:.84rem; color:#dce6f3; }
.workbench-tree-item:hover { background:#18283c; }
.workbench-tree-item small { color:var(--wb-muted); }
.workbench-workspace-shell { min-height:calc(100vh - 255px); border:1px solid var(--wb-line); border-radius:6px; background:radial-gradient(circle at 50% 20%,#142238 0,#0d141f 42%,#0b1018 100%); overflow:hidden; }
.workbench-workspace-empty { min-height:calc(100vh - 315px); display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:2.5rem; color:var(--wb-muted); }
.workbench-workspace-empty h2 { color:#f0f5fb; font-size:1.65rem; margin:.35rem 0; }
.workbench-workspace-empty .hero-icon { font-size:2.5rem; color:var(--wb-accent); }
.workbench-quick-actions { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.65rem; margin-top:1.25rem; width:min(42rem,100%); }
.workbench-quick-card { border:1px solid var(--wb-line); background:rgba(20,31,47,.82); border-radius:7px; padding:.9rem; color:#dce7f4; }
.workbench-las-card { border:1px solid var(--wb-line); background:#141f2e; border-radius:6px; padding:.65rem .75rem; }
.workbench-las-track { min-height:18rem; border:1px solid var(--wb-line); border-radius:6px; background:linear-gradient(180deg,#17253a,#0d141e); padding:.65rem; }
.workbench-property { display:grid; grid-template-columns:minmax(5rem,.8fr) minmax(0,1.2fr); gap:.5rem; padding:.48rem 0; border-bottom:1px solid #202c3e; font-size:.82rem; }
.workbench-property span:first-child { color:var(--wb-muted); }
.workbench-statusbar { display:flex; align-items:center; flex-wrap:wrap; gap:.45rem 1rem; min-height:30px; padding:.28rem .65rem; margin-top:.45rem; border:1px solid var(--wb-line); border-radius:5px; background:#101824; font-size:.72rem; }
.workbench-statusbar strong { color:#8da0b9; font-weight:500; }
.workbench-status-ready { margin-left:auto; color:var(--wb-success); font-weight:700; }
@media (min-width: 600px) { .workbench-ribbon { padding-left:.65rem; padding-right:.65rem; } }
@media (min-width: 1024px) { .workbench-titlebar { min-height:52px; } .workbench-main { grid-template-columns:minmax(14rem, 18rem) minmax(0, 1fr) minmax(16rem, 20rem); } }
@media (min-width: 1600px) { .workbench-workspace-shell { min-height:calc(100vh - 245px); } }
@media (max-width:1200px) { .workbench-quick-actions { grid-template-columns:1fr; } .workbench-titlebar h1{font-size:1.1rem;} }
@media (max-width: 1023px) { .workbench-main { grid-template-columns:1fr; } }
@media (max-width:900px) { .workbench-main { grid-template-columns:1fr; } .workbench-titlebar { align-items:flex-start; gap:.5rem; } .workbench-build{display:none;} .workbench-workspace-shell{min-height:32rem;} }
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



def _dispatch_action(
    contract: WorkbenchRendererContract,
    registry: WorkbenchCommandRegistry,
    action: dict[str, Any],
) -> CommandExecutionResult:
    controller = WorkbenchController(
        registry.state,
        renderer=contract.renderer,
        version=contract.version,
        command_registry=registry,
    )
    return controller.dispatch_renderer_action(
        str(action.get("id", "")), dict(action.get("payload", {}) or {})
    ).command_result


def _render_native_streamlit_layout(
    contract: WorkbenchRendererContract,
    registry: WorkbenchCommandRegistry,
    st_module: Any,
    payload: dict[str, Any],
    layout: dict[str, Any],
) -> tuple[CommandExecutionResult, ...]:
    """Render the professional five-region Workbench with native Streamlit containers."""

    executed: list[CommandExecutionResult] = []
    active_workspace = payload.get("interaction", {}).get("active_workspace") or "dashboard"
    build = runtime_build_info()
    st_module.markdown(
        "<header class='workbench-titlebar'>"
        "<div class='workbench-brand'><div class='workbench-logo'>⌁</div><div>"
        "<h1>Gas Ratio Pro — Modern Workbench</h1>"
        "<div class='workbench-subtitle'>Well-log analysis and interpretation workspace</div>"
        "</div></div>"
        f"<div class='workbench-build'>Build <b>{_html(build.version)}</b><br>Workspace: <b>{_html(active_workspace)}</b></div>"
        "</header>", unsafe_allow_html=True,
    )
    st_module.markdown(
        "<nav class='workbench-menu' aria-label='Main menu'>"
        + "".join(
            f"<span class='workbench-menu-item{' active' if i == 0 else ''}'>{_html(title)}</span>"
            for i, title in enumerate(("File", "Project", "Data", "LAS", "Interpretation", "Reports", "Export", "Settings", "Help"))
        )
        + "</nav>", unsafe_allow_html=True,
    )

    # Show only groups containing usable actions. The previous renderer created
    # seven equal-width columns even for empty groups, which caused tiny text,
    # clipped labels and large unused gaps.
    groups = [dict(group) for group in layout.get("toolbar", ()) if group.get("actions")]
    if groups:
        st_module.markdown("<div class='workbench-ribbon'><div class='workbench-ribbon-label'>Commands</div></div>", unsafe_allow_html=True)
        for group in groups:
            actions = [dict(a) for a in group.get("actions", ()) if a.get("id")]
            if not actions:
                continue
            st_module.markdown(
                f"<div class='workbench-ribbon-label'>{_html(group.get('title', 'Commands'))}</div>",
                unsafe_allow_html=True,
            )
            for offset in range(0, len(actions), 6):
                row = actions[offset:offset + 6]
                columns = st_module.columns(len(row), gap="small")
                for action, column in zip(row, columns):
                    with column:
                        ui_id = str(action.get("ui_id") or action.get("id"))
                        key = "workbench_toolbar_" + ui_id.replace(".", "_")
                        label = str(action.get("title") or action.get("label") or action.get("id"))
                        if st_module.button(label, key=key, disabled=not bool(action.get("enabled", True)), width="stretch"):
                            executed.append(_dispatch_action(contract, registry, action))

    dock_panes = {str(item.get("id")): dict(item) for item in payload.get("dock_panes", ())}
    explorer = dock_panes.get("dock.project_explorer", {})
    properties_pane = dock_panes.get("dock.properties", {})
    explorer_open = bool(explorer.get("opened", True)) and not bool(explorer.get("collapsed", False))
    properties_open = bool(properties_pane.get("opened", True)) and not bool(properties_pane.get("collapsed", False))
    widths = [1.15 if explorer_open else 0.09, 4.9, 1.35 if properties_open else 0.09]
    left, center, right = st_module.columns(widths, gap="small")

    kind_icons = {"project":"▣", "collection":"▸", "well":"◉", "las":"▤", "curve":"⌁"}
    with left:
        if explorer_open:
            st_module.markdown("<div class='workbench-pane-title'><span>Project Explorer</span><span>⌕</span></div>", unsafe_allow_html=True)
            for item in layout.get("project_tree", ()):
                indent = "&nbsp;" * (4 * int(item.get("level", 0)))
                icon = kind_icons.get(str(item.get("kind", "")), "•")
                count = f"<small>{int(item.get('count', 0))}</small>" if item.get("count") not in (None, "") else ""
                st_module.markdown(
                    f"<div class='workbench-tree-item'><span>{indent}{icon}&nbsp; {_html(item.get('title', ''))}</span>{count}</div>",
                    unsafe_allow_html=True,
                )
            collapse = {"id":"action.collapse_dock_pane", "payload":{"pane_id":"dock.project_explorer"}}
            if st_module.button("‹", key="workbench_native_collapse_explorer", help="Collapse Project Explorer"):
                executed.append(_dispatch_action(contract, registry, collapse))
        else:
            restore = {"id":"action.restore_dock_pane", "payload":{"pane_id":"dock.project_explorer"}}
            if st_module.button("›", key="workbench_native_restore_explorer", help="Restore Project Explorer"):
                executed.append(_dispatch_action(contract, registry, restore))

    workspace = dict(layout.get("workspace", {}) or {})
    with center:
        st_module.markdown(f"<div class='workbench-pane-title'><span>{_html(workspace.get('title', 'Workspace'))}</span><span>×</span></div>", unsafe_allow_html=True)
        st_module.markdown("<div class='workbench-workspace-shell'>", unsafe_allow_html=True)
        runtime = dict(workspace.get("runtime", {}) or {})
        visualization = dict(runtime.get("visualization", {}) or {})
        if runtime.get("embedded"):
            cards = list(workspace.get("content", {}).get("summary_cards", ()) or ())
            if cards:
                card_columns = st_module.columns(min(len(cards), 4), gap="small")
                for card, column in zip(cards, card_columns):
                    with column:
                        st_module.markdown(
                            "<div class='workbench-las-card'>"
                            f"<small>{_html(card.get('title', ''))}</small><br><b>{_html(card.get('value', ''))}</b></div>",
                            unsafe_allow_html=True,
                        )
            depth = dict(visualization.get("depth_range", {}) or {})
            st_module.markdown(
                f"<div style='padding:.55rem .7rem;color:#9fb0c6'>Depth viewport: <b>{_html(depth.get('start','—'))} – {_html(depth.get('stop','—'))} {_html(visualization.get('depth_unit',''))}</b></div>",
                unsafe_allow_html=True,
            )
            tracks = list(visualization.get("tracks", ()) or ())
            curves = list(visualization.get("curves", ()) or ())
            if tracks:
                track_columns = st_module.columns(min(len(tracks), 6), gap="small")
                for track, column in zip(tracks, track_columns):
                    with column:
                        track_id = str(track.get("id") or track.get("track_id") or "track")
                        labels = ", ".join(str(c.get("mnemonic") or c.get("title") or c.get("id") or "") for c in curves if str(c.get("track_id", "")) == track_id) or "No visible curves"
                        st_module.markdown(f"<article class='workbench-las-track'><h4>{_html(track.get('title') or track_id)}</h4><small>{_html(labels)}</small></article>", unsafe_allow_html=True)
            else:
                st_module.info("LAS is open, but no visible tracks are available.")
        else:
            st_module.markdown(
                "<div class='workbench-workspace-empty'><div class='hero-icon'>⌁</div>"
                "<h2>Modern Workbench</h2><p>Open a project or import a LAS file to begin interpretation.</p>"
                "<div class='workbench-quick-actions'>"
                "<div class='workbench-quick-card'><b>Open Project</b><br><small>Continue an existing workspace</small></div>"
                "<div class='workbench-quick-card'><b>Import LAS</b><br><small>Add well-log data</small></div>"
                "<div class='workbench-quick-card'><b>LAS Viewer</b><br><small>Inspect tracks and curves</small></div>"
                "</div></div>", unsafe_allow_html=True,
            )
        st_module.markdown("</div>", unsafe_allow_html=True)

    with right:
        if properties_open:
            st_module.markdown("<div class='workbench-pane-title'><span>Properties</span><span>⌘</span></div>", unsafe_allow_html=True)
            props_html = "".join(
                "<div class='workbench-property'>"
                f"<span>{_html(item.get('label',''))}</span><b>{_html(item.get('value',''))}</b></div>"
                for item in layout.get("properties", ())
            )
            st_module.markdown(props_html or "<small>No selection</small>", unsafe_allow_html=True)
            collapse = {"id":"action.collapse_dock_pane", "payload":{"pane_id":"dock.properties"}}
            if st_module.button("›", key="workbench_native_collapse_properties", help="Collapse Properties"):
                executed.append(_dispatch_action(contract, registry, collapse))
        else:
            restore = {"id":"action.restore_dock_pane", "payload":{"pane_id":"dock.properties"}}
            if st_module.button("‹", key="workbench_native_restore_properties", help="Restore Properties"):
                executed.append(_dispatch_action(contract, registry, restore))

    status_items = list(layout.get("status_items", ()))
    status_html = "".join(f"<span><strong>{_html(i.get('label',''))}:</strong> {_html(i.get('value',''))}</span>" for i in status_items)
    st_module.markdown(f"<footer class='workbench-statusbar' aria-label='Status bar'>{status_html}<span class='workbench-status-ready'>● Ready</span></footer>", unsafe_allow_html=True)
    return tuple(executed)

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
    if callable(getattr(st_module, "columns", None)):
        return _render_native_streamlit_layout(contract, registry, st_module, payload, layout)
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
    allowed_toolbar_actions = {
        str(action.get("ui_id") or action.get("id")): dict(action)
        for group in layout["toolbar"]
        for action in group.get("actions", [])
        if action.get("id") and action.get("enabled", True)
    }
    for ui_id, action in allowed_toolbar_actions.items():
        action_id = str(action.get("id"))
        label = str(action.get("title") or action.get("label") or action_id)
        key = "workbench_toolbar_" + ui_id.replace(".", "_")
        if st_module.button(label, key=key, disabled=not bool(action.get("enabled", True))):
            controller = WorkbenchController(
                registry.state, renderer=contract.renderer, version=contract.version, command_registry=registry
            )
            executed.append(controller.dispatch_renderer_action(action_id, dict(action.get("payload", {}) or {})).command_result)

    tree_html = "".join(
        f"<div class='workbench-tree-item' style='padding-left:{.45 + .8 * int(item.get('level', 0))}rem'>"
        f"<span>{_html(item['title'])}</span><small>{_html(item.get('count', ''))}</small></div>"
        for item in layout["project_tree"]
    )
    workspace = layout["workspace"]
    cards = workspace.get("content", {}).get("summary_cards", [])
    cards_html = "".join(f"<div class='workbench-las-card'><small>{_html(card.get('title'))}</small><b>{_html(card.get('value'))}</b></div>" for card in cards)
    runtime = dict(workspace.get("runtime", {}) or {})
    visualization = dict(runtime.get("visualization", {}) or {})
    track_html = ""
    if runtime.get("embedded"):
        curves = list(visualization.get("curves", ()) or ())
        for track in list(visualization.get("tracks", ()) or ()):
            track_id = str(track.get("id") or track.get("track_id") or "track")
            track_curves = [curve for curve in curves if str(curve.get("track_id", "")) == track_id]
            labels = ", ".join(str(curve.get("mnemonic") or curve.get("title") or curve.get("id") or "") for curve in track_curves[:8]) or "No visible curves"
            track_html += (
                f"<article class='workbench-las-track' aria-label='LAS track {_html(track_id)}'>"
                f"<h4>{_html(track.get('title') or track_id)}</h4>"
                f"<small>{_html(labels)}</small></article>"
            )
        depth = dict(visualization.get("depth_range", {}) or {})
        depth_text = f"{_html(depth.get('start', '—'))} – {_html(depth.get('stop', '—'))} {_html(visualization.get('depth_unit', ''))}"
        center_html = (
            f"<div class='workbench-las-summary'>{cards_html}"
            f"<div class='workbench-las-card'><small>Depth viewport</small><b>{depth_text}</b></div></div>"
            f"<div class='workbench-las-tracks'>{track_html}</div>"
        )
    else:
        center_html = (f"<div class='workbench-las-summary'>{cards_html}</div>" if cards_html else "") or f"<div class='workbench-workspace-empty'><h3>{_html(workspace['title'])}</h3><p>{_html(workspace['empty_state'])}</p></div>"
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
