"""Command-backed actions for Workbench tools.

Tool actions are small UI-neutral intents such as opening a LAS, running an
analysis preview or exporting the current report.  They deliberately do not
parse LAS files, run engineering calculations or render files directly.  The
service validates lightweight context, records the request and publishes events
so domain services can handle the action outside the UI layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, MutableMapping

from core.command_framework import WorkbenchCommand, WorkbenchCommandRegistry
from core.event_bus import ApplicationEventBus
from core.application_state import ApplicationStateController
from core.workbench_context import WorkspaceContext, WorkbenchSelectionService
from core.workbench_tools import WorkbenchToolManager
from core.workspace_session import SESSION_ACTIVE_REPORT_KEY, SESSION_RECENT_EXPORTS_KEY, SESSION_SELECTED_INTERVALS_KEY

WORKBENCH_OPEN_LAS_COMMAND_ID = "workbench.tool.open_las"
WORKBENCH_RUN_GAS_RATIO_ANALYSIS_COMMAND_ID = "workbench.tool.run_gas_ratio_analysis"
WORKBENCH_REFRESH_REPORT_PREVIEW_COMMAND_ID = "workbench.tool.refresh_report_preview"
WORKBENCH_EXPORT_REPORT_BUNDLE_COMMAND_ID = "workbench.tool.export_report_bundle"

WORKBENCH_TOOL_ACTION_HISTORY_KEY = "workbench_tool_action_history"
WORKBENCH_LAST_TOOL_ACTION_KEY = "workbench_last_tool_action"


@dataclass(frozen=True, slots=True)
class WorkbenchToolActionResult:
    """Serializable result of a tool action request."""

    action_id: str
    tool_id: str
    accepted: bool
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "tool_id": self.tool_id,
            "accepted": self.accepted,
            "message": self.message,
            "payload": dict(self.payload),
            "context": dict(self.context),
        }


class WorkbenchToolActionService:
    """Validates and records Workbench tool actions through command handlers."""

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state
        self.event_bus = ApplicationEventBus(state)

    def _context(self) -> WorkspaceContext:
        return WorkspaceContext.from_state(self.state)

    def _remember(self, result: WorkbenchToolActionResult) -> WorkbenchToolActionResult:
        payload = result.to_dict()
        history = list(self.state.get(WORKBENCH_TOOL_ACTION_HISTORY_KEY, ()) or ())
        history.append(payload)
        self.state[WORKBENCH_TOOL_ACTION_HISTORY_KEY] = history[-50:]
        self.state[WORKBENCH_LAST_TOOL_ACTION_KEY] = payload
        self.event_bus.publish("workbench.tool_action.executed", payload, source="WorkbenchToolActionService")
        return result

    def _activate_tool(self, tool_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Mirror accepted workflow actions to the active Workbench tool."""

        WorkbenchToolManager(self.state).activate(tool_id, metadata=metadata or {})

    def _set_selected_intervals(self, interval_ids: list[str]) -> list[str]:
        """Persist interval selections while keeping existing order stable."""

        merged: list[str] = []
        for item in list(self.state.get(SESSION_SELECTED_INTERVALS_KEY, ()) or ()) + list(interval_ids):
            text = str(item or "").strip()
            if text and text not in merged:
                merged.append(text)
        self.state[SESSION_SELECTED_INTERVALS_KEY] = merged
        return merged

    def _remember_recent_export(self, report_id: str, formats: list[str]) -> list[str]:
        """Store a lightweight export request descriptor in recent exports."""

        descriptor = f"{report_id}:{','.join(formats)}"
        recent = [str(item) for item in (self.state.get(SESSION_RECENT_EXPORTS_KEY, ()) or ()) if str(item or "").strip()]
        recent = [item for item in recent if item != descriptor]
        recent.append(descriptor)
        self.state[SESSION_RECENT_EXPORTS_KEY] = recent[-20:]
        return list(self.state[SESSION_RECENT_EXPORTS_KEY])

    def open_las(self, payload: dict[str, Any] | None = None) -> WorkbenchToolActionResult:
        clean_payload = dict(payload or {})
        context = self._context()
        las_id = str(clean_payload.get("las_id") or context.application.las_id or "").strip()
        accepted = bool(las_id)
        if accepted:
            ApplicationStateController(self.state).activate_las(las_id)
            WorkbenchSelectionService(self.state).select("las", las_id, {"source": "tool_action", **dict(clean_payload.get("metadata", {}) or {})})
            self._activate_tool("tool.las_viewer", {"action_id": WORKBENCH_OPEN_LAS_COMMAND_ID, "las_id": las_id})
            context = self._context()
        result = WorkbenchToolActionResult(
            WORKBENCH_OPEN_LAS_COMMAND_ID,
            "tool.las_viewer",
            accepted,
            "LAS open request accepted." if accepted else "Select a LAS before opening the LAS viewer.",
            {"las_id": las_id, **clean_payload},
            context.to_dict(),
        )
        return self._remember(result)

    def run_gas_ratio_analysis(self, payload: dict[str, Any] | None = None) -> WorkbenchToolActionResult:
        clean_payload = dict(payload or {})
        context = self._context()
        intervals = list(clean_payload.get("interval_ids") or context.selected_intervals or ())
        if context.selection.target == "interval" and context.selection.object_id not in intervals:
            intervals.append(context.selection.object_id)
        intervals = [str(item).strip() for item in intervals if str(item or "").strip()]
        accepted = bool(context.application.las_id and intervals)
        if accepted:
            intervals = self._set_selected_intervals(intervals)
            WorkbenchSelectionService(self.state).select("interval", intervals[-1], {"source": "tool_action", "las_id": context.application.las_id})
            self._activate_tool("tool.gas_ratio_analysis", {"action_id": WORKBENCH_RUN_GAS_RATIO_ANALYSIS_COMMAND_ID, "interval_ids": intervals})
            context = self._context()
        result = WorkbenchToolActionResult(
            WORKBENCH_RUN_GAS_RATIO_ANALYSIS_COMMAND_ID,
            "tool.gas_ratio_analysis",
            accepted,
            "Gas ratio analysis request accepted." if accepted else "Select a LAS and at least one interval before running analysis.",
            {"las_id": context.application.las_id, "interval_ids": intervals, **clean_payload},
            context.to_dict(),
        )
        return self._remember(result)

    def refresh_report_preview(self, payload: dict[str, Any] | None = None) -> WorkbenchToolActionResult:
        clean_payload = dict(payload or {})
        context = self._context()
        report_id = str(clean_payload.get("report_id") or context.active_report or "").strip()
        accepted = bool(report_id)
        if accepted:
            self.state[SESSION_ACTIVE_REPORT_KEY] = report_id
            WorkbenchSelectionService(self.state).select("report", report_id, {"source": "tool_action"})
            self._activate_tool("tool.report_preview", {"action_id": WORKBENCH_REFRESH_REPORT_PREVIEW_COMMAND_ID, "report_id": report_id})
            context = self._context()
        result = WorkbenchToolActionResult(
            WORKBENCH_REFRESH_REPORT_PREVIEW_COMMAND_ID,
            "tool.report_preview",
            accepted,
            "Report preview refresh request accepted." if accepted else "Select or create a report before refreshing preview.",
            {"report_id": report_id, **clean_payload},
            context.to_dict(),
        )
        return self._remember(result)

    def export_report_bundle(self, payload: dict[str, Any] | None = None) -> WorkbenchToolActionResult:
        clean_payload = dict(payload or {})
        context = self._context()
        report_id = str(clean_payload.get("report_id") or context.active_report or "").strip()
        formats = [str(item).strip() for item in (clean_payload.get("formats") or ["html", "pdf", "docx"]) if str(item or "").strip()]
        accepted = bool(report_id)
        recent_exports: list[str] = []
        if accepted:
            self.state[SESSION_ACTIVE_REPORT_KEY] = report_id
            recent_exports = self._remember_recent_export(report_id, formats)
            self._activate_tool("tool.export", {"action_id": WORKBENCH_EXPORT_REPORT_BUNDLE_COMMAND_ID, "report_id": report_id})
            context = self._context()
        result = WorkbenchToolActionResult(
            WORKBENCH_EXPORT_REPORT_BUNDLE_COMMAND_ID,
            "tool.export",
            accepted,
            "Export bundle request accepted." if accepted else "Select or create a report before exporting.",
            {"report_id": report_id, "formats": formats, "recent_exports": recent_exports, **clean_payload},
            context.to_dict(),
        )
        return self._remember(result)


def register_workbench_tool_action_commands(
    state: MutableMapping[str, Any],
    registry: WorkbenchCommandRegistry | None = None,
    service: WorkbenchToolActionService | None = None,
) -> WorkbenchCommandRegistry:
    """Register tool action commands used by renderers and tool view buttons."""

    command_registry = registry or WorkbenchCommandRegistry(state)
    action_service = service or WorkbenchToolActionService(state)

    command_registry.register(
        WorkbenchCommand(WORKBENCH_OPEN_LAS_COMMAND_ID, "Открыть LAS", "tool", "Запросить открытие выбранного LAS через command layer.", icon="well"),
        lambda payload: action_service.open_las(payload).to_dict(),
        replace=True,
    )
    command_registry.register(
        WorkbenchCommand(WORKBENCH_RUN_GAS_RATIO_ANALYSIS_COMMAND_ID, "Запустить анализ газовых коэффициентов", "tool", "Запросить расчет выбранных интервалов через command layer.", icon="ratio"),
        lambda payload: action_service.run_gas_ratio_analysis(payload).to_dict(),
        replace=True,
    )
    command_registry.register(
        WorkbenchCommand(WORKBENCH_REFRESH_REPORT_PREVIEW_COMMAND_ID, "Обновить предпросмотр отчета", "tool", "Запросить обновление report preview через command layer.", icon="report"),
        lambda payload: action_service.refresh_report_preview(payload).to_dict(),
        replace=True,
    )
    command_registry.register(
        WorkbenchCommand(WORKBENCH_EXPORT_REPORT_BUNDLE_COMMAND_ID, "Экспортировать отчет", "tool", "Запросить экспорт HTML PDF DOCX пакета через command layer.", icon="export"),
        lambda payload: action_service.export_report_bundle(payload).to_dict(),
        replace=True,
    )
    return command_registry
