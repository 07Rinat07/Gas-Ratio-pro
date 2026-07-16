"""Streamlit adapter for the Modern Workbench renderer contract.

The adapter is intentionally thin: it renders the already prepared
``WorkbenchRendererContract`` payload and dispatches action command ids through
``WorkbenchCommandRegistry``.  It does not calculate interpretations, mutate
workspace data directly, perform exports or persist domain objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import json
import mimetypes
from typing import Any, MutableMapping, Protocol

from core.command_framework import CommandExecutionResult, WorkbenchCommandRegistry
from core.build_info import runtime_build_info
from core.workbench_controller import WorkbenchController, build_workbench_controller
from core.application_service_container import application_service_container
from projects.repository import DEFAULT_PROJECTS_ROOT
from core.internationalization.language_registry import SUPPORTED_LANGUAGES, normalize_language
from core.workbench_ui_layout import build_workbench_ui_layout
from core.workbench_property_actions import (
    WORKBENCH_PROPERTY_ACTION_COMMAND_ID, WORKBENCH_PROPERTY_TECHNICAL_KEY,
)
from core.workbench_project_explorer import (
    explorer_kind_icon,
    explorer_status_marker,
    filter_project_explorer_nodes,
    visible_project_explorer_nodes,
)
from core.diagnostics_center import build_diagnostics_center_snapshot
from core.workbench_runtime_diagnostics import (
    diagnostics_enabled, diagnostics_snapshot, record_binding_state, record_runtime_exception,
)
from core.workbench_shell import (
    WorkbenchRendererContract,
    WorkbenchShellBuilder,
    build_workbench_renderer_contract,
)

WORKBENCH_RENDERER_NAME = "streamlit-modern"
WORKBENCH_RENDERER_CONTRACT_VERSION = "workbench-renderer-contract"
WORKBENCH_LAST_UI_ACTION_KEY = "workbench_last_ui_action"
WORKBENCH_MENU_PANEL_KEY = "workbench_menu_panel"
WORKBENCH_LANGUAGE_KEY = "user_settings.interface_language"
_I18N_DIR = Path(__file__).resolve().parents[1] / "resources" / "i18n"
_USER_LOCALE_PATH = Path(__file__).resolve().parents[1] / "data" / "user_preferences" / "locale.json"


def _localization_context(registry: WorkbenchCommandRegistry, st_module: Any):
    """Resolve, persist and return the session localization service."""
    container = application_service_container(registry.state)
    preferences = container.user_locale_preferences(path=_USER_LOCALE_PATH)
    stored = registry.state.get(WORKBENCH_LANGUAGE_KEY)
    language = normalize_language(stored if stored is not None else preferences.load())
    localization = container.localization(catalogs_dir=_I18N_DIR, language=language)
    localization.set_language(language)

    # Real Streamlit pages use a persistent website-style RU / ҚАЗ / EN switcher.
    # Small test doubles that do not expose columns/button keep the selectbox fallback.
    columns = getattr(st_module, "columns", None)
    button = getattr(st_module, "button", None)
    if callable(columns) and callable(button):
        labels = {"ru": "RU", "kk": "ҚАЗ", "en": "EN"}
        st_module.markdown("<div class='workbench-language-switcher-label'>" + localization("language.label") + "</div>", unsafe_allow_html=True)
        language_columns = columns(3, gap="small")
        selected = language
        for code, column in zip(tuple(SUPPORTED_LANGUAGES), language_columns):
            with column:
                if st_module.button(
                    labels[code],
                    key=f"workbench_language_button_{code}",
                    width="stretch",
                    type="primary" if code == language else "secondary",
                    help=localization(f"language.{code}"),
                ):
                    selected = code
        selected = normalize_language(selected)
        if selected != language:
            language = preferences.save(selected)
            registry.state[WORKBENCH_LANGUAGE_KEY] = language
            localization.set_language(language)
            rerun = getattr(st_module, "rerun", None)
            if callable(rerun):
                rerun()
    else:
        selectbox = getattr(st_module, "selectbox", None)
        if callable(selectbox):
            codes = tuple(SUPPORTED_LANGUAGES)
            selected = selectbox(
                localization("language.label"),
                options=codes,
                index=codes.index(language),
                format_func=lambda code: localization(f"language.{code}"),
                key="workbench_language_selector",
                help=localization("language.preference.help"),
            )
            selected = normalize_language(selected)
            if selected != language:
                language = preferences.save(selected)
                registry.state[WORKBENCH_LANGUAGE_KEY] = language
                localization.set_language(language)
        else:
            registry.state[WORKBENCH_LANGUAGE_KEY] = language
    return localization


def _branding_logo_data_uri() -> str:
    """Return the shared application logo as a data URI for the title bar."""
    path = Path(__file__).resolve().parents[1] / "assets" / "branding" / "gas_ratio_pro_logo.png"
    if not path.exists():
        return ""
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


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
.block-container { max-width:100% !important; padding:2.65rem .55rem .2rem !important; }
[data-testid="stHeader"] { height:2.2rem; background:rgba(11,16,24,.96); }
[data-testid="stToolbar"] { top:.15rem; }
.workbench-titlebar { position:relative; z-index:2; display:flex; align-items:center; justify-content:space-between; min-height:48px; padding:.25rem .55rem; border-bottom:1px solid var(--wb-line); background:linear-gradient(180deg,#121c2a,#0e151f); }
.workbench-brand { display:flex; gap:.65rem; align-items:center; }
.workbench-logo-image { width:38px; height:38px; object-fit:contain; flex:0 0 auto; }
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
.workbench-command-feedback { margin:.35rem .55rem; padding:.42rem .65rem; border:1px solid #2e5944; border-radius:5px; background:#10251b; color:#b9f3d1; font-size:.78rem; }
[data-testid="stHorizontalBlock"] { gap:.55rem; }
div[data-testid="stButton"] > button { min-height: 44px; border-radius:6px; border:1px solid #344760; background:linear-gradient(180deg,#1b2a3d,#142031); color:#f1f6fd; font-size:.82rem; font-weight:600; padding:.45rem .65rem; box-shadow:none; }
div[data-testid="stButton"] > button:hover { border-color:#4e8be8; background:linear-gradient(180deg,#233752,#182943); color:white; }
div[data-testid="stButton"] > button:focus-visible { outline:3px solid rgba(77,159,255,.75); outline-offset:2px; }
.workbench-pane-title { display:flex; align-items:center; justify-content:space-between; min-height:36px; padding:.45rem .65rem; margin-bottom:.4rem; border-bottom:1px solid var(--wb-line); background:#131d2a; font-weight:700; font-size:.9rem; }
.workbench-tree-item { padding:.43rem .5rem; border-radius:5px; margin:.08rem 0; display:flex; align-items:center; justify-content:space-between; font-size:.84rem; color:#dce6f3; }
.workbench-tree-item:hover { background:#18283c; }
.workbench-tree-item small { color:var(--wb-muted); }
.workbench-workspace-shell { border:1px solid var(--wb-line); border-radius:6px; background:radial-gradient(circle at 50% 20%,#142238 0,#0d141f 42%,#0b1018 100%); overflow:hidden; }
.workbench-workspace-empty { min-height:calc(100vh - 315px); display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:2.5rem; color:var(--wb-muted); }
.workbench-workspace-empty h2 { color:#f0f5fb; font-size:1.65rem; margin:.35rem 0; }
.workbench-workspace-context { display:flex; align-items:center; gap:.45rem; padding:.45rem .65rem; border-bottom:1px solid var(--wb-line); color:var(--wb-muted); font-size:.78rem; }
.workbench-workspace-context b { color:#dce8f8; }
.workbench-empty-actions { width:min(44rem,100%); margin-top:.85rem; }
.workbench-workspace-empty .hero-icon { font-size:2.5rem; color:var(--wb-accent); }
.workbench-quick-actions { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.65rem; margin-top:1.25rem; width:min(42rem,100%); }
.workbench-quick-card { border:1px solid var(--wb-line); background:rgba(20,31,47,.82); border-radius:7px; padding:.9rem; color:#dce7f4; }
.workbench-las-card { border:1px solid var(--wb-line); background:#141f2e; border-radius:6px; padding:.65rem .75rem; }
.workbench-las-track { min-height:18rem; border:1px solid var(--wb-line); border-radius:6px; background:linear-gradient(180deg,#17253a,#0d141e); padding:.65rem; }
.workbench-property { display:grid; grid-template-columns:minmax(5rem,.8fr) minmax(0,1.2fr); gap:.5rem; padding:.48rem 0; border-bottom:1px solid #202c3e; font-size:.82rem; }
.workbench-property span:first-child { color:var(--wb-muted); }
.workbench-properties-empty { padding:.8rem; border:1px dashed var(--wb-line); border-radius:6px; color:var(--wb-muted); line-height:1.45; }
.workbench-properties-empty b { color:var(--wb-text); }
.workbench-statusbar { display:flex; align-items:center; flex-wrap:wrap; gap:.45rem 1rem; min-height:30px; padding:.28rem .65rem; margin-top:.45rem; border:1px solid var(--wb-line); border-radius:5px; background:#101824; font-size:.72rem; }
.workbench-statusbar strong { color:#8da0b9; font-weight:500; }
.workbench-status-ready { margin-left:auto; color:var(--wb-success); font-weight:700; }
@media (min-width: 600px) { .workbench-ribbon { padding-left:.65rem; padding-right:.65rem; } }
@media (min-width: 1024px) { .workbench-titlebar { min-height:52px; } .workbench-main { grid-template-columns:minmax(14rem, 18rem) minmax(0, 1fr) minmax(16rem, 20rem); } }
@media (min-width: 1600px) { .workbench-workspace-empty { min-height:calc(100vh - 315px); } }
@media (max-width:1200px) { .workbench-quick-actions { grid-template-columns:1fr; } .workbench-titlebar h1{font-size:1.1rem;} }
@media (max-width: 1023px) { .workbench-main { grid-template-columns:1fr; } }
@media (max-width:900px) { .workbench-main { grid-template-columns:1fr; } .workbench-titlebar { align-items:flex-start; gap:.5rem; } .workbench-build{display:none;} .workbench-workspace-empty{min-height:28rem;} }
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
    result = controller.dispatch_renderer_action(
        str(action.get("id", "")), dict(action.get("payload", {}) or {})
    ).command_result
    registry.state[WORKBENCH_LAST_UI_ACTION_KEY] = {
        "action_id": str(action.get("id", "")),
        "title": str(action.get("title") or action.get("label") or action.get("id") or "Command"),
        "executed": bool(result.executed),
        "message": str(result.message or ""),
    }
    return result


def _render_native_streamlit_layout(
    contract: WorkbenchRendererContract,
    registry: WorkbenchCommandRegistry,
    st_module: Any,
    payload: dict[str, Any],
    layout: dict[str, Any],
) -> tuple[CommandExecutionResult, ...]:
    """Render the professional five-region Workbench with native Streamlit containers."""

    executed: list[CommandExecutionResult] = []
    i18n = _localization_context(registry, st_module)
    active_workspace = payload.get("interaction", {}).get("active_workspace") or "dashboard"
    build = runtime_build_info()
    logo_uri = _branding_logo_data_uri()
    logo_html = (
        f"<img class='workbench-logo-image' src='{logo_uri}' alt='Gas Ratio Pro logo'>"
        if logo_uri else "<div class='workbench-logo'>⌁</div>"
    )
    st_module.markdown(
        "<header class='workbench-titlebar'>"
        f"<div class='workbench-brand'>{logo_html}<div>"
        f"<h1>{_html(i18n('app.workbench.title'))}</h1>"
        f"<div class='workbench-subtitle'>{_html(i18n('app.workbench.subtitle'))}</div>"
        "</div></div>"
        f"<div class='workbench-build'>{_html(i18n('app.build'))} <b>{_html(build.version)}</b><br>{_html(i18n('app.workspace'))}: <b>{_html(active_workspace)}</b></div>"
        "</header>", unsafe_allow_html=True,
    )
    menu_items = (
        (i18n("menu.file"), "menu.file"),
        (i18n("menu.project"), "menu.project"),
        (i18n("menu.data"), "nav.data"),
        (i18n("menu.las"), "nav.las_workspace"),
        (i18n("menu.correlation"), "nav.correlation"),
        (i18n("menu.interpretation"), "nav.interpretation"),
        (i18n("menu.reports"), "nav.reports"),
        (i18n("menu.export"), "nav.exports"),
        (i18n("menu.settings"), "nav.dashboard"),
        (i18n("menu.help"), "nav.documentation"),
    )
    active_navigation_id = str(payload.get("interaction", {}).get("active_navigation_id", "") or "")
    menu_columns = st_module.columns(len(menu_items), gap="small")
    for (title, navigation_id), column in zip(menu_items, menu_columns):
        with column:
            is_panel = navigation_id.startswith("menu.")
            active = (navigation_id == active_navigation_id) if not is_panel else (registry.state.get(WORKBENCH_MENU_PANEL_KEY) == navigation_id)
            if st_module.button(
                title,
                key=f"workbench_menu_{title.lower()}",
                width="stretch",
                disabled=False,
                type="primary" if active else "secondary",
                help=i18n("menu.open_help", title=title),
            ):
                if is_panel:
                    registry.state[WORKBENCH_MENU_PANEL_KEY] = "" if active else navigation_id
                else:
                    registry.state[WORKBENCH_MENU_PANEL_KEY] = ""
                    executed.append(
                        _dispatch_action(
                            contract,
                            registry,
                            {
                                "id": "action.select_navigation",
                                "title": title,
                                "payload": {"navigation_id": navigation_id},
                            },
                        )
                    )

    panel_id = str(registry.state.get(WORKBENCH_MENU_PANEL_KEY, "") or "")
    if panel_id == "menu.file":
        st_module.markdown(f"### {i18n('menu.file.title')}")
        file_cols = st_module.columns(3, gap="small")
        with file_cols[0]:
            if st_module.button(i18n("menu.file.open_project"), key="workbench_file_open_project", width="stretch"):
                registry.state[WORKBENCH_MENU_PANEL_KEY] = "menu.project"
        with file_cols[1]:
            if st_module.button(i18n("menu.file.restore_session"), key="workbench_file_restore_session", width="stretch"):
                try:
                    service = application_service_container(registry.state).workbench(projects_root=DEFAULT_PROJECTS_ROOT)
                    result = service.restore_recent_session()
                    registry.state[WORKBENCH_LAST_UI_ACTION_KEY] = {"action_id":"restore_recent_session","title":i18n("menu.file.restore_session"),"executed":True,"message":result.kind}
                except Exception as exc:
                    incident = record_runtime_exception(registry.state, exc, boundary="file_menu", operation="restore_recent_session")
                    st_module.error(i18n("menu.file.restore_error", error_id=incident["correlation_id"]))
        with file_cols[2]:
            if st_module.button(i18n("menu.file.close"), key="workbench_file_close", width="stretch"):
                registry.state[WORKBENCH_MENU_PANEL_KEY] = ""
    elif panel_id == "menu.project":
        st_module.markdown(f"### {i18n('menu.project.title')}")
        try:
            service = application_service_container(registry.state).workbench(projects_root=DEFAULT_PROJECTS_ROOT)
            entries = service.project_entries()
            if entries:
                for entry in entries:
                    cols = st_module.columns([4,1], gap="small")
                    with cols[0]:
                        st_module.caption(f"{entry['project_name']} · {entry['project_id']}")
                    with cols[1]:
                        if st_module.button(i18n("common.open"), key=f"workbench_project_open_{entry['project_id']}", width="stretch", disabled=not entry['available']):
                            result = service.open_project(entry['project_id'])
                            registry.state[WORKBENCH_LAST_UI_ACTION_KEY] = {"action_id":"open_project","title":i18n("menu.file.open_project"),"executed":True,"message":result.project_id}
                            registry.state[WORKBENCH_MENU_PANEL_KEY] = ""
            else:
                st_module.info(i18n("menu.project.no_recent"))
        except Exception as exc:
            incident = record_runtime_exception(registry.state, exc, boundary="project_menu", operation="list_projects")
            st_module.error(i18n("menu.project.load_error", error_id=incident["correlation_id"]))

    # Show only commands that are meaningful in the current presentation state.
    # Active navigation is highlighted, redundant tool activation is hidden, and
    # mutually exclusive dock commands never appear together.
    dock_state = {str(item.get("id")): dict(item) for item in payload.get("dock_panes", ())}

    def _visible_action(action: dict[str, Any]) -> bool:
        action_id = str(action.get("id", ""))
        # Navigation belongs to the single top menu and Project Explorer.
        # Dock controls live on the pane rails.  Repeating either group in the
        # ribbon creates a third navigation level and visual noise.
        if action_id in {
            "action.activate_tool",
            "action.select_navigation",
            "action.collapse_dock_pane",
            "action.restore_dock_pane",
        }:
            return False
        return True

    groups: list[dict[str, Any]] = []
    for raw_group in layout.get("toolbar", ()):
        actions = [dict(action) for action in raw_group.get("actions", ()) if action.get("id") and _visible_action(dict(action))]
        if actions:
            group = dict(raw_group)
            group["actions"] = actions
            groups.append(group)

    if groups:
        st_module.markdown(f"<div class='workbench-ribbon'><div class='workbench-ribbon-label'>{_html(i18n('common.commands'))}</div></div>", unsafe_allow_html=True)
        for group in groups:
            actions = list(group.get("actions", ()))
            st_module.markdown(
                f"<div class='workbench-ribbon-label'>{_html(group.get('title', 'Commands'))}</div>",
                unsafe_allow_html=True,
            )
            for offset in range(0, len(actions), 5):
                row = actions[offset:offset + 5]
                columns = st_module.columns([1] * len(row) + [1.15] * max(0, 5 - len(row)), gap="small")
                for action, column in zip(row, columns):
                    with column:
                        ui_id = str(action.get("ui_id") or action.get("id"))
                        key = "workbench_toolbar_" + ui_id.replace(".", "_")
                        action_id = str(action.get("id", ""))
                        nav_id = str(action.get("payload", {}).get("navigation_id", ""))
                        active = action_id == "action.select_navigation" and nav_id == active_navigation_id
                        label = str(action.get("title") or action.get("label") or action_id)
                        if active:
                            label = "● " + label
                        if st_module.button(
                            label,
                            key=key,
                            disabled=not bool(action.get("enabled", True)) or active,
                            width="stretch",
                            type="primary" if active else "secondary",
                            help=("Current workspace" if active else f"Open {label.replace('● ', '')}"),
                        ):
                            executed.append(_dispatch_action(contract, registry, action))

    feedback = registry.state.get(WORKBENCH_LAST_UI_ACTION_KEY)
    if isinstance(feedback, dict) and feedback.get("executed"):
        st_module.markdown(
            "<div class='workbench-command-feedback'>✓ "
            f"{_html(feedback.get('title', 'Command'))}: {_html(feedback.get('message') or i18n('common.completed'))}</div>",
            unsafe_allow_html=True,
        )

    dock_panes = {str(item.get("id")): dict(item) for item in payload.get("dock_panes", ())}
    explorer = dock_panes.get("dock.project_explorer", {})
    properties_pane = dock_panes.get("dock.properties", {})
    explorer_open = bool(explorer.get("opened", True)) and not bool(explorer.get("collapsed", False))
    properties_open = bool(properties_pane.get("opened", True)) and not bool(properties_pane.get("collapsed", False))
    widths = [1.15 if explorer_open else 0.10, 4.9, 1.35 if properties_open else 0.10]
    left, center, right = st_module.columns(widths, gap="small")

    with left:
        if explorer_open:
            st_module.markdown(f"<div class='workbench-pane-title'><span>{_html(i18n('project.explorer.title'))}</span><span>⌕</span></div>", unsafe_allow_html=True)
            raw_tree = tuple(dict(item) for item in layout.get("project_tree", ()) or ())
            query = ""
            if hasattr(st_module, "text_input"):
                query = str(
                    st_module.text_input(
                        i18n("project.explorer.search.label"),
                        key="workbench_project_explorer_search",
                        placeholder=i18n("project.explorer.search.placeholder"),
                        label_visibility="collapsed",
                    )
                    or ""
                )
            filtered_view = filter_project_explorer_nodes(raw_tree, query)
            all_parent_ids = {
                str(item.get("parent_id") or "")
                for item in raw_tree
                if str(item.get("parent_id") or "")
            }
            root_ids = [str(item.get("id") or "") for item in raw_tree if not str(item.get("parent_id") or "")]
            expanded_key = "workbench_project_explorer_expanded"
            expanded_ids = set(registry.state.get(expanded_key, root_ids) or root_ids)
            if query.strip():
                expanded_ids.update(all_parent_ids)
            visible_tree = visible_project_explorer_nodes(
                filtered_view.nodes,
                expanded_ids,
                force_expand=bool(query.strip()),
            )
            if query.strip() and hasattr(st_module, "caption"):
                st_module.caption(
                    i18n("project.explorer.matches", matched=filtered_view.matched_nodes, total=filtered_view.total_nodes)
                )
            if query.strip() and not filtered_view.nodes:
                if hasattr(st_module, "info"):
                    st_module.info(i18n("project.explorer.no_results"))
            selected_state = dict(registry.state.get("workbench_selection", {}) or {})
            selected_target = str(selected_state.get("target") or "")
            selected_object_id = str(selected_state.get("object_id") or "")
            for item in visible_tree:
                item_id = str(item.get("id", ""))
                level = int(item.get("level", 0))
                kind = str(item.get("kind", ""))
                has_children = bool(item.get("has_children", False) or item_id in all_parent_ids)
                is_expanded = item_id in expanded_ids
                icon = explorer_kind_icon(kind)
                marker = explorer_status_marker(item)
                count = item.get("count")
                expander_symbol = "▾" if has_children and is_expanded else ("▸" if has_children else " ")
                label = f"{'  ' * level}{expander_symbol} {marker} {icon} {item.get('title', '')}"
                if count not in (None, "") and has_children:
                    label += f" ({int(count)})"
                navigation_id = str(item.get("navigation_id") or "").strip()
                selectable = bool(item.get("selectable", False))
                target = str(item.get("target") or ("collection" if navigation_id else "")).strip()
                object_id = str(item.get("object_id") or item_id).strip()
                metadata = dict(item.get("metadata", {}) or {})
                metadata.setdefault("title", str(item.get("title") or ""))
                metadata.setdefault("kind", kind)
                metadata.setdefault("status", str(item.get("status") or ""))
                if count not in (None, ""):
                    metadata.setdefault("count", int(count))
                if navigation_id:
                    metadata.setdefault("navigation_id", navigation_id)
                active_object = target == selected_target and object_id == selected_object_id
                if navigation_id or selectable or has_children:
                    if st_module.button(
                        label,
                        key=f"workbench_tree_{item_id.replace('.', '_').replace(':', '_')}",
                        width="stretch",
                        type="primary" if active_object else "secondary",
                        help=str(item.get("status") or i18n("project.explorer.select_help")),
                    ):
                        if has_children:
                            if item_id in expanded_ids:
                                expanded_ids.remove(item_id)
                            else:
                                expanded_ids.add(item_id)
                                section_by_folder = {
                                    "folder:custom": "custom",
                                    "folder:wells": "wells",
                                    "folder:calculations": "calculations",
                                    "folder:datasets": "datasets",
                                    "folder:imports": "imports",
                                    "folder:exports": "exports",
                                }
                                requested_section = section_by_folder.get(item_id)
                                if requested_section:
                                    requested_sections = set(
                                        registry.state.get(
                                            "workbench_project_explorer_requested_sections", ()
                                        ) or ()
                                    )
                                    requested_sections.add(requested_section)
                                    registry.state[
                                        "workbench_project_explorer_requested_sections"
                                    ] = sorted(requested_sections)
                            registry.state[expanded_key] = sorted(expanded_ids)
                        controller = WorkbenchController(
                            registry.state,
                            renderer=contract.renderer,
                            version=contract.version,
                            command_registry=registry,
                        )
                        if target and object_id and selectable:
                            controller.select_object(target, object_id, metadata)
                        if navigation_id and navigation_id != active_navigation_id:
                            executed.append(
                                dispatch_workbench_renderer_action(
                                    contract, registry, "action.select_navigation", {"navigation_id": navigation_id}
                                )
                            )
                else:
                    st_module.markdown(f"<div class='workbench-tree-item'>{_html(label)}</div>", unsafe_allow_html=True)
            collapse = {"id":"action.collapse_dock_pane", "payload":{"pane_id":"dock.project_explorer"}}
            if st_module.button("‹", key="workbench_native_collapse_explorer", help=i18n("project.explorer.collapse")):
                executed.append(_dispatch_action(contract, registry, collapse))
        else:
            restore = {"id":"action.restore_dock_pane", "payload":{"pane_id":"dock.project_explorer"}}
            if st_module.button("›", key="workbench_native_restore_explorer", help=i18n("project.explorer.restore")):
                executed.append(_dispatch_action(contract, registry, restore))

    workspace = dict(layout.get("workspace", {}) or {})
    with center:
        st_module.markdown(f"<div class='workbench-pane-title'><span>{_html(workspace.get('title') or i18n('workspace.title'))}</span><span>×</span></div>", unsafe_allow_html=True)
        st_module.markdown(
            f"<div class='workbench-workspace-context'>{_html(i18n('workspace.host'))}: "
            f"<b>{_html(payload.get('interaction', {}).get('active_navigation_id', '') or 'dashboard')}</b></div>",
            unsafe_allow_html=True,
        )
        runtime = dict(workspace.get("runtime", {}) or {})
        visualization = dict(runtime.get("visualization", {}) or {})
        active_navigation_id = str(payload.get("interaction", {}).get("active_navigation_id", "") or "")
        real_streamlit = str(getattr(st_module, "__name__", "")) == "streamlit"
        module_rendered = False
        if real_streamlit:
            try:
                from app.streamlit_app import render_modern_workbench_workspace
                module_rendered = bool(render_modern_workbench_workspace(active_navigation_id))
                render_audit = diagnostics_snapshot(registry.state).get("render_audit", {})
                record_binding_state(
                    registry.state, route_id=active_navigation_id,
                    renderer=str(render_audit.get("renderer") or "render_modern_workbench_workspace"),
                    provider=str(render_audit.get("provider") or "existing-production-workflow"),
                    module_loaded=module_rendered and bool(render_audit.get("success", True)),
                    project_id=str(payload.get("interaction", {}).get("active_project_id", "") or ""),
                    details={
                        "phase": render_audit.get("phase", ""),
                        "duration_ms": render_audit.get("duration_ms"),
                        "expected_controls": render_audit.get("expected_controls", ()),
                    },
                )
            except Exception as exc:
                incident = record_runtime_exception(
                    registry.state, exc, boundary="workspace_renderer",
                    operation=active_navigation_id or "unknown-route",
                    context={"workspace": active_workspace},
                )
                record_binding_state(
                    registry.state, route_id=active_navigation_id,
                    renderer="render_modern_workbench_workspace",
                    provider="existing-production-workflow",
                    module_loaded=False,
                    details={"correlation_id": incident["correlation_id"]},
                )
                st_module.error(
                    i18n("error.workspace_open", error_id=incident["correlation_id"])
                )
        if module_rendered:
            pass
        elif runtime.get("embedded"):
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
            workspace_id = str(workspace.get("active_workspace") or active_workspace or "dashboard")
            empty_title = str(workspace.get("title") or i18n("workspace.empty.title"))
            empty_text = str(workspace.get("empty_state") or i18n("workspace.empty.text"))
            st_module.markdown(
                f"<div class='workbench-workspace-context'>{_html(i18n('workspace.active'))}: "
                f"<b>{_html(workspace_id)}</b></div>",
                unsafe_allow_html=True,
            )
            st_module.markdown(
                "<div class='workbench-workspace-empty'><div class='hero-icon'>⌁</div>"
                f"<h2>{_html(empty_title)}</h2><p>{_html(empty_text)}</p>"
                "<div class='workbench-quick-actions'>"
                f"<div class='workbench-quick-card'><b>{_html(i18n('workspace.quick.las.title'))}</b><br><small>{_html(i18n('workspace.quick.las.text'))}</small></div>"
                f"<div class='workbench-quick-card'><b>{_html(i18n('workspace.quick.interpretation.title'))}</b><br><small>{_html(i18n('workspace.quick.interpretation.text'))}</small></div>"
                f"<div class='workbench-quick-card'><b>{_html(i18n('workspace.quick.reports.title'))}</b><br><small>{_html(i18n('workspace.quick.reports.text'))}</small></div>"
                "</div></div>", unsafe_allow_html=True,
            )
            quick_actions = (
                (i18n("workspace.quick.open_las"), "nav.las_workspace"),
                (i18n("workspace.quick.open_interpretation"), "nav.interpretation"),
                (i18n("workspace.quick.open_reports"), "nav.reports"),
            )
            st_module.markdown("<div class='workbench-empty-actions'>", unsafe_allow_html=True)
            quick_columns = st_module.columns(3, gap="small")
            for (label, navigation_id), column in zip(quick_actions, quick_columns):
                with column:
                    if st_module.button(
                        label,
                        key=f"workbench_quick_{navigation_id.replace('.', '_')}",
                        width="stretch",
                        disabled=navigation_id == active_navigation_id,
                        type="primary" if navigation_id == active_navigation_id else "secondary",
                    ):
                        executed.append(
                            dispatch_workbench_renderer_action(
                                contract, registry, "action.select_navigation", {"navigation_id": navigation_id}
                            )
                        )
            st_module.markdown("</div>", unsafe_allow_html=True)

    with right:
        if properties_open:
            st_module.markdown(f"<div class='workbench-pane-title'><span>{_html(i18n('common.properties'))}</span><span>⌘</span></div>", unsafe_allow_html=True)
            props_html = "".join(
                "<div class='workbench-property'>"
                f"<span>{_html(item.get('label',''))}</span><b>{_html(item.get('value',''))}</b></div>"
                for item in layout.get("properties", ())
            )
            st_module.markdown(
                props_html or (f"<div class='workbench-properties-empty'><b>{_html(i18n('properties.empty.title'))}</b><br><small>{_html(i18n('properties.empty.text'))}</small></div>"),
                unsafe_allow_html=True,
            )

            action_result = dict(layout.get("property_action_result", {}) or {})
            if action_result.get("message"):
                if action_result.get("success"):
                    st_module.success(str(action_result.get("message")))
                else:
                    st_module.error(str(action_result.get("message")))

            selection = dict(payload.get("context", {}).get("selection", {}) or {})
            target = str(selection.get("target") or "")
            object_id = str(selection.get("object_id") or "")
            metadata = dict(selection.get("metadata", {}) or {})
            if (
                target == "dataset"
                and object_id
                and bool(metadata.get("downloadable"))
                and hasattr(st_module, "download_button")
            ):
                try:
                    from app.streamlit_app import LAS_CORRELATION_PROJECTS_ROOT, _application_state_controller
                    from core.application_service_container import application_service_container

                    active_project_id = str(payload.get("interaction", {}).get("active_project_id", "") or "")
                    if active_project_id:
                        data_platform = application_service_container(
                            _application_state_controller().state
                        ).data_platform(root=LAS_CORRELATION_PROJECTS_ROOT)
                        file_name, format_id, content = data_platform.read_registered_artifact(
                            active_project_id, object_id
                        )
                        mime_by_format = {
                            "pdf": "application/pdf",
                            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        }
                        st_module.download_button(
                            i18n("qc.panel.download_export"),
                            data=content,
                            file_name=file_name,
                            mime=mime_by_format.get(format_id, "application/octet-stream"),
                            key=f"workbench_download_dataset_{object_id}",
                            width="stretch",
                        )
                except Exception as exc:
                    if hasattr(st_module, "warning"):
                        st_module.warning(i18n("qc.panel.download_failed", error=str(exc)))

            property_actions = tuple(layout.get("property_actions", ()) or ())
            if property_actions and target and object_id:
                st_module.markdown(f"#### {i18n('properties.actions')}")
                confirmation = st_module.text_input(
                    i18n("properties.confirmation"),
                    value="",
                    key=f"workbench_properties_confirm_{target}_{object_id}",
                    placeholder=object_id,
                    help=i18n("properties.confirmation.help"),
                )
                for action in property_actions:
                    action_id = str(action.get("id") or "")
                    title = str(action.get("title") or action_id)
                    requires_confirmation = bool(action.get("requires_confirmation"))
                    confirmed = (not requires_confirmation) or confirmation.strip() == object_id
                    if st_module.button(
                        title,
                        key=f"workbench_properties_action_{target}_{object_id}_{action_id}",
                        width="stretch",
                        type="primary" if action_id == "open" else "secondary",
                        disabled=requires_confirmation and not confirmed,
                    ):
                        if action_id == "technical":
                            registry.state[WORKBENCH_PROPERTY_TECHNICAL_KEY] = not bool(
                                registry.state.get(WORKBENCH_PROPERTY_TECHNICAL_KEY, False)
                            )
                            executed.append(CommandExecutionResult(
                                WORKBENCH_PROPERTY_ACTION_COMMAND_ID, True,
                                message=i18n("properties.technical_toggled"), result={"technical": True}
                            ))
                        else:
                            executed.append(registry.execute(
                                WORKBENCH_PROPERTY_ACTION_COMMAND_ID,
                                {
                                    "action_id": action_id,
                                    "target": target,
                                    "object_id": object_id,
                                    "metadata": metadata,
                                    "confirmed": confirmed,
                                },
                            ))
            collapse = {"id":"action.collapse_dock_pane", "payload":{"pane_id":"dock.properties"}}
            if st_module.button("›", key="workbench_native_collapse_properties", help=i18n("properties.collapse")):
                executed.append(_dispatch_action(contract, registry, collapse))
        else:
            restore = {"id":"action.restore_dock_pane", "payload":{"pane_id":"dock.properties"}}
            if st_module.button("‹", key="workbench_native_restore_properties", help=i18n("properties.restore")):
                executed.append(_dispatch_action(contract, registry, restore))

        if properties_open and diagnostics_enabled() and hasattr(st_module, "expander"):
            snapshot = diagnostics_snapshot(registry.state)
            with st_module.expander(i18n("diagnostics.title"), expanded=False):
                binding = snapshot.get("binding", {})
                render_audit = snapshot.get("render_audit", {})
                st_module.caption(
                    i18n("diagnostics.binding", route=binding.get("route_id") or "—", renderer=binding.get("renderer") or "—", provider=binding.get("provider") or "—", loaded=i18n("common.yes") if binding.get("module_loaded") else i18n("common.no"))
                )
                if render_audit:
                    st_module.caption(
                        i18n("diagnostics.render", phase=render_audit.get("phase") or "—", success=i18n("common.yes") if render_audit.get("success") else i18n("common.no"), duration=render_audit.get("duration_ms") or "—")
                    )
                    controls = tuple(render_audit.get("expected_controls", ()) or ())
                    if controls:
                        st_module.caption(i18n("diagnostics.expected_controls", controls=", ".join(map(str, controls))))
                incidents = list(snapshot.get("incidents", ()))
                if incidents:
                    latest = incidents[-1]
                    st_module.error(
                        f"{latest.get('correlation_id')}: {latest.get('exception_type')} — {latest.get('message')}"
                    )
                else:
                    st_module.success(i18n("diagnostics.no_incidents"))

                center = build_diagnostics_center_snapshot(
                    registry.state,
                    performance_budgets_ms={
                        "las_correlation.total": 10000.0,
                        "las_correlation.figure": 5000.0,
                        "las_correlation.frontend": 3000.0,
                    },
                )
                runtime = dict(center.get("runtime", {}) or {})
                cache = dict(center.get("cache", {}) or {})
                repository_io = dict(center.get("repository", {}) or {})
                traces = dict(center.get("traces", {}) or {})
                session = dict(center.get("session", {}) or {})
                dataframe_memory = dict(center.get("dataframe_memory", {}) or {})
                route_lifecycle = dict(center.get("route_lifecycle", {}) or {})
                route_data = dict(center.get("route_data", {}) or {})
                project_navigation_cache = dict(center.get("project_navigation_cache", {}) or {})
                repository_health = dict(center.get("repository_health", {}) or {})
                registry_stats = dict(runtime.get("registry", {}) or {})
                cache_summary = dict(cache.get("summary", {}) or {})

                startup = dict(center.get("startup", {}) or {})
                latest_startup = dict(startup.get("latest", {}) or {})
                if latest_startup:
                    st_module.markdown("##### " + i18n("diagnostics.section.startup"))
                    st_module.caption(
                        "Status: " + str(latest_startup.get("status", "—"))
                        + " | Total: " + str(latest_startup.get("total_ms", 0.0)) + " ms"
                        + " | Slow stages: " + str(len(latest_startup.get("slow_stages", ()) or ()))
                    )
                    startup_stages = list(latest_startup.get("stages", ()) or ())
                    if startup_stages and hasattr(st_module, "dataframe"):
                        st_module.dataframe(startup_stages, width="stretch", hide_index=True)

                st_module.markdown("##### " + i18n("diagnostics.section.route_lifecycle"))
                st_module.caption(
                    "Active: " + str(route_lifecycle.get("active_route") or "—")
                    + " | Switches: " + str(route_lifecycle.get("transition_count", 0))
                    + " | Slow: " + str(route_lifecycle.get("slow_transition_count", 0))
                    + " | Cleanup failures: " + str(route_lifecycle.get("cleanup_failures", 0))
                    + " | Budget: " + str(route_lifecycle.get("switch_budget_ms", 0.0)) + " ms"
                )
                route_events = list(route_lifecycle.get("events", ()) or ())
                if route_events and hasattr(st_module, "dataframe"):
                    st_module.dataframe(route_events, width="stretch", hide_index=True)

                st_module.markdown("##### " + i18n("diagnostics.section.route_data"))
                st_module.caption(
                    "Events: " + str(route_data.get("event_count", 0))
                    + " | Slow: " + str(route_data.get("slow_count", 0))
                    + " | Navigation hits: " + str(route_data.get("navigation_cache_hits", 0))
                    + " | Misses: " + str(route_data.get("navigation_cache_misses", 0))
                    + " | Budget: " + str(route_data.get("budget_ms", 0.0)) + " ms"
                )
                route_data_events = list(route_data.get("events", ()) or ())
                if route_data_events and hasattr(st_module, "dataframe"):
                    st_module.dataframe(route_data_events, width="stretch", hide_index=True)
                st_module.caption(
                    "Navigation runtime cache: " + str(project_navigation_cache.get("entries", 0))
                    + "/" + str(project_navigation_cache.get("max_projects", 0))
                    + " projects | Hit rate: " + str(project_navigation_cache.get("hit_rate_percent", 0.0)) + "%"
                    + " | Invalidations: " + str(project_navigation_cache.get("invalidations", 0))
                    + " | Evictions: " + str(project_navigation_cache.get("evictions", 0))
                    + " | Last reason: " + str(project_navigation_cache.get("last_reason", "not-used"))
                )

                st_module.markdown("##### " + i18n("diagnostics.section.runtime"))
                st_module.caption(
                    "Services: " + str(registry_stats.get("active", 0))
                    + " | Created: " + str(registry_stats.get("created", 0))
                    + " | Replaced: " + str(registry_stats.get("replaced", 0))
                    + " | Events: " + str(runtime.get("event_count", 0))
                )
                services = list(runtime.get("services", ()) or ())
                service_scopes = dict(runtime.get("service_scopes", {}) or {})
                if services and hasattr(st_module, "dataframe"):
                    service_rows = [
                        {**item, "scope": service_scopes.get(str(item.get("key") or ""), "session")}
                        for item in services
                    ]
                    st_module.dataframe(service_rows, width="stretch", hide_index=True)

                st_module.markdown("##### " + i18n("diagnostics.section.cache"))
                st_module.caption(
                    "Hit rate: " + str(cache_summary.get("hit_rate", 0.0)) + "%"
                    + " | Hits: " + str(cache_summary.get("hits", 0))
                    + " | Misses: " + str(cache_summary.get("misses", 0))
                    + " | Entries: " + str(cache_summary.get("entries", 0))
                )
                caches = list(cache.get("caches", ()) or ())
                if caches and hasattr(st_module, "dataframe"):
                    st_module.dataframe(caches, width="stretch", hide_index=True)

                st_module.markdown("##### " + i18n("diagnostics.section.dataframe_memory"))
                st_module.caption(
                    "Entries: " + str(dataframe_memory.get("sample_entries", 0))
                    + " | Current: " + str(round(float(dataframe_memory.get("sample_bytes", 0)) / 1048576.0, 2)) + " MiB"
                    + " | Peak: " + str(round(float(dataframe_memory.get("peak_sample_bytes", 0)) / 1048576.0, 2)) + " MiB"
                    + " | Budget: " + str(round(float(dataframe_memory.get("max_sample_bytes", 0)) / 1048576.0, 2)) + " MiB"
                    + " | Utilization: " + str(dataframe_memory.get("memory_utilization_percent", 0.0)) + "%"
                )
                if int(dataframe_memory.get("oversized_skips", 0) or 0):
                    st_module.warning(i18n("diagnostics.oversized_samples", count=dataframe_memory.get("oversized_skips", 0)))

                st_module.markdown("##### " + i18n("diagnostics.section.repository_io"))
                st_module.caption(
                    "Reads: " + str(repository_io.get("reads", 0))
                    + " | Writes: " + str(repository_io.get("writes", 0))
                    + " | Failures: " + str(repository_io.get("failures", 0))
                    + " | Avg: " + str(repository_io.get("average_duration_ms", 0.0)) + " ms"
                )
                mutation_info = dict(repository_io.get("mutations", {}) or {})
                st_module.caption(
                    "Mutations: " + str(mutation_info.get("mutation_count", 0))
                    + " | Subscribers: " + str(mutation_info.get("subscriber_count", 0))
                    + " | Notification failures: " + str(mutation_info.get("mutation_failures", 0))
                )
                st_module.caption(
                    "Transactions: " + str(mutation_info.get("transaction_count", 0))
                    + " | Rollbacks: " + str(mutation_info.get("transaction_failures", 0))
                    + " | Last ID: "
                    + str(dict(mutation_info.get("last_transaction", {}) or {}).get("transaction_id", ""))[:12]
                )
                st_module.caption(
                    "Recovered after interruption: " + str(mutation_info.get("recovery_count", 0))
                    + " | Recovery failures: " + str(mutation_info.get("recovery_failures", 0))
                )
                st_module.caption(
                    "Integrity checks: " + str(mutation_info.get("integrity_checks", 0))
                    + " | Integrity failures: " + str(mutation_info.get("integrity_failures", 0))
                    + " | Quarantined journals: " + str(mutation_info.get("quarantined_transactions", 0))
                    + " | Cleaned journals: " + str(mutation_info.get("cleaned_transactions", 0))
                )
                transaction_rows = list(mutation_info.get("recent_transactions", ()) or ())
                if transaction_rows and hasattr(st_module, "dataframe"):
                    st_module.dataframe(transaction_rows[-10:], width="stretch", hide_index=True)
                repository_events = list(repository_io.get("events", ()) or ())
                if repository_events and hasattr(st_module, "dataframe"):
                    st_module.dataframe(repository_events, width="stretch", hide_index=True)

                st_module.markdown("##### " + i18n("diagnostics.section.repository_health"))
                severity_counts = dict(repository_health.get("severity_counts", {}) or {})
                st_module.caption(
                    "Status: " + ("healthy" if repository_health.get("healthy", True) else "issues detected")
                    + " | Files: " + str(repository_health.get("files_scanned", 0))
                    + " | JSON: " + str(repository_health.get("json_files", 0))
                    + " | Errors: " + str(severity_counts.get("error", 0))
                    + " | Warnings: " + str(severity_counts.get("warning", 0))
                    + " | Repairable: " + str(repository_health.get("repairable_count", 0))
                    + " | Scan: " + str(repository_health.get("duration_ms", 0.0)) + " ms"
                )
                health_issues = list(repository_health.get("issues", ()) or ())
                if health_issues and hasattr(st_module, "dataframe"):
                    st_module.dataframe(health_issues[:50], width="stretch", hide_index=True)
                readiness = dict(repository_health.get("readiness", {}) or {})
                schedule = dict(repository_health.get("schedule", {}) or {})
                st_module.caption(
                    "Recovery readiness: " + str(readiness.get("score", 100)) + "/100"
                    + " (" + str(readiness.get("status", "ready")) + ")"
                    + " | Scheduled scans: " + str(schedule.get("scan_count", 0))
                    + " | Skipped: " + str(schedule.get("skipped_count", 0))
                    + " | Failures: " + str(schedule.get("failure_count", 0))
                )
                if repository_health.get("truncated"):
                    st_module.warning(i18n("diagnostics.repository_scan_truncated"))

                st_module.markdown("##### " + i18n("diagnostics.section.traces"))
                trace_summary = dict(traces.get("summary", {}) or {})
                st_module.caption(
                    "Events: " + str(trace_summary.get("events", 0))
                    + " | Slow: " + str(trace_summary.get("slow_events", 0))
                    + " | Failed: " + str(trace_summary.get("failed_events", 0))
                    + " | Max: " + str(trace_summary.get("maximum_duration_ms", 0.0)) + " ms"
                )
                trace_events = list(traces.get("events", ()) or ())
                if trace_events and hasattr(st_module, "dataframe"):
                    st_module.dataframe(trace_events, width="stretch", hide_index=True)

                st_module.markdown("##### " + i18n("diagnostics.section.session"))
                st_module.caption(
                    "Keys: " + str(session.get("total_keys", 0))
                    + " | Runtime: " + str(session.get("runtime_count", 0))
                    + " | Transient: " + str(session.get("transient_count", 0))
                    + " | Unscoped: " + str(len(session.get("unscoped_keys", ()) or ()))
                )
                owner_counts = dict(session.get("owner_counts", {}) or {})
                lifecycle_counts = dict(session.get("lifecycle_counts", {}) or {})
                if owner_counts:
                    st_module.caption(
                        "Owners: " + ", ".join(f"{key}={value}" for key, value in owner_counts.items())
                    )
                if lifecycle_counts:
                    st_module.caption(
                        "Lifecycle: " + ", ".join(f"{key}={value}" for key, value in lifecycle_counts.items())
                    )
                unregistered = list(session.get("unregistered_keys", ()) or ())
                if unregistered:
                    st_module.warning(i18n("diagnostics.unregistered_keys", keys=", ".join(unregistered[:12])))

                budgets = list(center.get("budgets", ()) or ())
                if budgets:
                    st_module.markdown("##### " + i18n("diagnostics.section.budgets"))
                    if hasattr(st_module, "dataframe"):
                        st_module.dataframe(budgets, width="stretch", hide_index=True)

                st_module.markdown("##### " + i18n("diagnostics.dataset_catalog.title"))
                active_project_id = str(payload.get("interaction", {}).get("active_project_id", "") or "")
                if active_project_id:
                    if st_module.button(
                        i18n("diagnostics.dataset_catalog.rebuild"),
                        key="workbench_diagnostics_rebuild_dataset_catalog",
                        width="stretch",
                    ):
                        data_platform = application_service_container(registry.state).data_platform(root=DEFAULT_PROJECTS_ROOT)
                        reconciliation = data_platform.reconcile_catalog(active_project_id)
                        st_module.success(
                            i18n(
                                "diagnostics.dataset_catalog.result",
                                status=reconciliation.get("status", "—"),
                                manifest_count=reconciliation.get("manifest_count", 0),
                                catalog_count_before=reconciliation.get("catalog_count_before", 0),
                            )
                        )
                else:
                    st_module.caption(i18n("diagnostics.dataset_catalog.no_project"))

                baseline = dict(center.get("performance_baseline", {}) or {})
                if baseline:
                    st_module.markdown("##### " + i18n("diagnostics.section.baseline"))
                    st_module.caption(
                        "Stages: " + str(len(baseline.get("stages", {}) or {}))
                        + " | Cache hit rate: " + str(baseline.get("cache_hit_rate", 0.0)) + "%"
                        + " | Session keys: " + str(baseline.get("session_keys", 0))
                        + " | Failed events: " + str(baseline.get("failed_events", 0))
                    )
                    if hasattr(st_module, "download_button"):
                        st_module.download_button(
                            i18n("diagnostics.download_baseline"),
                            data=json.dumps(baseline, ensure_ascii=False, indent=2),
                            file_name="gasratio-performance-baseline.json",
                            mime="application/json",
                            key="workbench_diagnostics_performance_baseline_download",
                        )

    status_items = list(layout.get("status_items", ()))
    status_html = "".join(f"<span><strong>{_html(i.get('label',''))}:</strong> {_html(i.get('value',''))}</span>" for i in status_items)
    st_module.markdown(
        f"<footer class='workbench-statusbar' aria-label='{_html(i18n('status.bar.label'))}'>"
        f"{status_html}<span class='workbench-status-ready'>● {_html(i18n('status.ready'))}</span></footer>",
        unsafe_allow_html=True,
    )
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
