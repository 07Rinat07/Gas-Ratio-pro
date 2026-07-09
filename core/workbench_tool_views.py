"""Renderer-facing view models for Workbench tools.

The tool view layer translates registered tools and current Workbench state into
small serializable payloads.  It intentionally contains no Streamlit imports and
no engineering calculations.  Renderers receive these view models, display them,
and send actions back to the controller.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, MutableMapping, Protocol

from services.las_curve_metadata_service import LasCurveMetadataService
from services.las_visualization_payload_service import LasVisualizationPayloadService
from core.workbench_context import WorkspaceContext
from core.workbench_tools import WorkbenchToolDescriptor, WorkbenchToolManager, WorkbenchToolRegistry


@dataclass(frozen=True, slots=True)
class WorkbenchToolViewModel:
    """Serializable renderer contract for one Workbench tool.

    ``content`` is intentionally lightweight.  It contains ids, labels, summary
    cards and renderer hints, never parsed LAS tables or calculated engineering
    results.  Domain services can later hydrate the selected ids outside the UI.
    """

    id: str
    title: str
    category: str
    icon: str = ""
    active: bool = False
    open: bool = False
    enabled: bool = True
    supported_targets: tuple[str, ...] = field(default_factory=tuple)
    status: str = "available"
    empty_state: str = ""
    renderer_hint: str = "placeholder"
    actions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    content: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible payload for UI renderers."""

        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "icon": self.icon,
            "active": self.active,
            "open": self.open,
            "enabled": self.enabled,
            "supported_targets": list(self.supported_targets),
            "status": self.status,
            "empty_state": self.empty_state,
            "renderer_hint": self.renderer_hint,
            "actions": [dict(action) for action in self.actions],
            "metadata": dict(self.metadata),
            "content": dict(self.content),
        }


def _default_empty_state(tool: WorkbenchToolDescriptor, context: WorkspaceContext) -> str:
    """Build a human-readable empty state without touching domain services."""

    if tool.id == "tool.las_viewer":
        return "Open or import a LAS file to inspect curves."
    if tool.id == "tool.log_viewer":
        return "Select a LAS curve to preview log tracks."
    if tool.id == "tool.gas_ratio_analysis":
        return "Select an interval with gas data to run gas ratio interpretation."
    if tool.id == "tool.report_preview":
        return "Generate or select an engineering report to preview it."
    if tool.id == "tool.export":
        return "Create an engineering report before exporting HTML PDF or DOCX."
    if tool.id == "tool.settings":
        return "Configure workspace presentation and reporting options."
    if context.application.workspace_id:
        return "Workspace tool is ready."
    return "Open a workspace to use this tool."


def _tool_status(tool: WorkbenchToolDescriptor, context: WorkspaceContext) -> str:
    """Return lightweight readiness status based on context only."""

    if not tool.enabled:
        return "disabled"
    targets = set(tool.supported_targets)
    if "las" in targets and not context.application.las_id:
        return "waiting_for_las"
    if "report" in targets and not context.active_report:
        return "waiting_for_report"
    if "workspace" in targets and not context.application.workspace_id:
        return "waiting_for_workspace"
    return "ready"


def _renderer_hint(tool: WorkbenchToolDescriptor) -> str:
    mapping = {
        "tool.workspace_explorer": "tree",
        "tool.las_viewer": "las_curve_viewer",
        "tool.log_viewer": "log_track_viewer",
        "tool.gas_ratio_analysis": "interpretation_panel",
        "tool.report_preview": "report_preview",
        "tool.export": "export_panel",
        "tool.settings": "settings_panel",
    }
    return mapping.get(tool.id, str(tool.factory or "placeholder") or "placeholder")


def _context_summary(context: WorkspaceContext) -> dict[str, str]:
    """Return stable ids shared by multiple tool view providers."""

    return {
        "project_id": context.application.project_id,
        "well_id": context.application.well_id,
        "las_id": context.application.las_id,
        "workspace_id": context.application.workspace_id,
    }


def _action(action_id: str, title: str, payload: dict[str, Any], *, enabled: bool = True) -> dict[str, Any]:
    return {"id": action_id, "title": title, "payload": dict(payload), "enabled": bool(enabled)}


def build_tool_view_model(
    tool: WorkbenchToolDescriptor,
    *,
    active_tool_id: str,
    open_tool_ids: Iterable[str],
    context: WorkspaceContext,
) -> WorkbenchToolViewModel:
    """Create one renderer-facing view model from a tool descriptor."""

    opened = set(open_tool_ids)
    status = _tool_status(tool, context)
    metadata = dict(tool.metadata or {})
    metadata.update({"factory": tool.factory, "order": tool.order})
    actions = (
        _action(
            "action.activate_tool",
            "Activate tool",
            {"tool_id": tool.id},
            enabled=bool(tool.enabled),
        ),
    )
    return WorkbenchToolViewModel(
        id=tool.id,
        title=tool.title,
        category=tool.category,
        icon=tool.icon,
        active=tool.id == active_tool_id,
        open=tool.id in opened,
        enabled=tool.enabled,
        supported_targets=tuple(tool.supported_targets),
        status=status,
        empty_state=_default_empty_state(tool, context),
        renderer_hint=_renderer_hint(tool),
        actions=actions,
        metadata=metadata,
        content={"context": _context_summary(context)},
    )


class WorkbenchToolViewProvider(Protocol):
    """Contract for UI-neutral tool view providers."""

    tool_id: str

    def build(
        self,
        base: WorkbenchToolViewModel,
        context: WorkspaceContext,
        state: MutableMapping[str, Any],
    ) -> WorkbenchToolViewModel:
        """Return a tool-specific renderer view model."""


class LasViewerToolViewProvider:
    """Builds the LAS Viewer content contract from lightweight context ids."""

    tool_id = "tool.las_viewer"

    def build(self, base: WorkbenchToolViewModel, context: WorkspaceContext, state: MutableMapping[str, Any]) -> WorkbenchToolViewModel:
        las_id = context.application.las_id
        if not las_id:
            return base
        content = dict(base.content)
        selected_las = {
            "project_id": context.application.project_id,
            "well_id": context.application.well_id,
            "las_id": las_id,
        }
        metadata_summary: dict[str, Any] = {}
        visualization_payload: dict[str, Any] = {}
        visualization_error = ""
        metadata_error = ""
        if context.application.project_id:
            try:
                metadata_summary = LasCurveMetadataService(state.get("projects_root") or state.get("project_root") or "projects").summarize(
                    context.application.project_id,
                    las_id,
                ).to_dict()
                selected_las["well_id"] = metadata_summary.get("well_id") or selected_las["well_id"]
                selected_las["well_name"] = metadata_summary.get("well_name", "")
                visualization_payload = LasVisualizationPayloadService(state.get("projects_root") or state.get("project_root") or "projects").build(
                    context.application.project_id,
                    las_id,
                    interval_ids=context.selected_intervals,
                    interval_metadata=state.get("workspace_interval_metadata") or state.get("interval_metadata"),
                ).to_dict()
            except Exception as exc:  # renderer payload must remain safe even if storage is unavailable
                metadata_error = str(exc)
                visualization_error = str(exc)
        content.update(
            {
                "selected_las": selected_las,
                "summary_cards": [
                    {"title": "Project", "value": context.application.project_id or "not selected"},
                    {"title": "Well", "value": selected_las.get("well_name") or context.application.well_id or selected_las.get("well_id") or "not selected"},
                    {"title": "LAS", "value": las_id},
                    {"title": "Curves", "value": str(metadata_summary.get("curve_count", "not loaded"))},
                ],
                "available_sections": ["curve_overview", "depth_range", "quality_flags"],
                "curve_metadata": metadata_summary,
                "visualization": visualization_payload,
                "visualization_error": visualization_error,
                "metadata_error": metadata_error,
            }
        )
        actions = tuple(base.actions) + (
            _action("action.open_las", "Open selected LAS", {"las_id": las_id}, enabled=True),
        )
        metadata = dict(base.metadata)
        metadata.update({"primary_target": "las", "selected_las_id": las_id})
        return replace(
            base,
            status="ready",
            empty_state="",
            actions=actions,
            metadata=metadata,
            content=content,
        )


class GasRatioAnalysisToolViewProvider:
    """Builds the gas-ratio analysis panel contract without running calculations."""

    tool_id = "tool.gas_ratio_analysis"

    def build(self, base: WorkbenchToolViewModel, context: WorkspaceContext, state: MutableMapping[str, Any]) -> WorkbenchToolViewModel:
        selected_intervals = list(context.selected_intervals)
        selected_interval = context.selection.object_id if context.selection.target == "interval" else ""
        if selected_interval and selected_interval not in selected_intervals:
            selected_intervals.append(selected_interval)
        if not context.application.las_id:
            return base
        status = "ready" if selected_intervals else "waiting_for_interval"
        content = dict(base.content)
        content.update(
            {
                "las_id": context.application.las_id,
                "selected_intervals": selected_intervals,
                "active_interval": selected_interval or (selected_intervals[0] if selected_intervals else ""),
                "available_sections": ["ratio_summary", "fluid_type", "confidence", "recommendations"],
            }
        )
        actions = tuple(base.actions) + (
            _action(
                "action.select_navigation",
                "Open interpretation workspace",
                {"navigation_id": "nav.interpretation"},
                enabled=True,
            ),
            _action(
                "action.run_gas_ratio_analysis",
                "Run gas ratio analysis",
                {"las_id": context.application.las_id, "interval_ids": selected_intervals},
                enabled=bool(selected_intervals),
            ),
        )
        metadata = dict(base.metadata)
        metadata.update({"primary_target": "interval", "interval_count": len(selected_intervals)})
        return replace(
            base,
            status=status,
            empty_state="" if selected_intervals else "Select an interpreted interval to show gas ratio results.",
            actions=actions,
            metadata=metadata,
            content=content,
        )


class ReportPreviewToolViewProvider:
    """Builds the report preview contract from current report/session ids."""

    tool_id = "tool.report_preview"

    def build(self, base: WorkbenchToolViewModel, context: WorkspaceContext, state: MutableMapping[str, Any]) -> WorkbenchToolViewModel:
        if not context.active_report:
            return base
        content = dict(base.content)
        content.update(
            {
                "report": {
                    "report_id": context.active_report,
                    "plot_id": context.active_plot,
                    "selected_intervals": list(context.selected_intervals),
                },
                "available_sections": ["engineering_conclusion", "intervals", "recommendations"],
            }
        )
        actions = tuple(base.actions) + (
            _action("action.refresh_report_preview", "Refresh preview", {"report_id": context.active_report}, enabled=True),
            _action("action.export_report_bundle", "Export report bundle", {"report_id": context.active_report, "formats": ["html", "pdf", "docx"]}, enabled=True),
            _action("action.activate_tool", "Open export", {"tool_id": "tool.export"}, enabled=True),
        )
        metadata = dict(base.metadata)
        metadata.update({"primary_target": "report", "active_report_id": context.active_report})
        return replace(base, status="ready", empty_state="", actions=actions, metadata=metadata, content=content)


DEFAULT_TOOL_VIEW_PROVIDERS: tuple[WorkbenchToolViewProvider, ...] = (
    LasViewerToolViewProvider(),
    GasRatioAnalysisToolViewProvider(),
    ReportPreviewToolViewProvider(),
)


class WorkbenchToolViewService:
    """Build tool view models for the controller and renderer contract."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        providers: Iterable[WorkbenchToolViewProvider] | None = None,
    ) -> None:
        self.state = state
        self.registry = WorkbenchToolRegistry(state)
        self.manager = WorkbenchToolManager(state, self.registry)
        self.providers = {provider.tool_id: provider for provider in (providers or DEFAULT_TOOL_VIEW_PROVIDERS)}

    def build_one(self, tool: WorkbenchToolDescriptor, context: WorkspaceContext) -> WorkbenchToolViewModel:
        """Build one provider-enriched tool view model."""

        base = build_tool_view_model(
            tool,
            active_tool_id=self.manager.active_tool_id(),
            open_tool_ids=self.manager.open_tool_ids(),
            context=context,
        )
        provider = self.providers.get(tool.id)
        return provider.build(base, context, self.state) if provider is not None else base

    def build_all(self, context: WorkspaceContext) -> tuple[WorkbenchToolViewModel, ...]:
        return tuple(self.build_one(tool, context) for tool in self.registry.list())

    def active(self, context: WorkspaceContext) -> WorkbenchToolViewModel | None:
        active_id = self.manager.active_tool_id()
        for view in self.build_all(context):
            if view.id == active_id:
                return view
        return None

    def payload(self, context: WorkspaceContext) -> dict[str, Any]:
        views = self.build_all(context)
        active = next((view for view in views if view.active), None)
        return {
            "active_tool_id": active.id if active is not None else "",
            "active_tool": active.to_dict() if active is not None else None,
            "items": [view.to_dict() for view in views],
            "open_tool_ids": [view.id for view in views if view.open],
            "provider_ids": sorted(self.providers),
        }
