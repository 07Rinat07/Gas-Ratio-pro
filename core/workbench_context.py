"""Workspace context and selection services for Modern Workbench.

This module contains framework-neutral coordination state used by the
Workbench controller and lifecycle manager.  It deliberately stores lightweight
identifiers only: selected LAS/report/interval/plot ids, current shell state and
renderer metadata.  Heavy calculation tables and rendered charts remain outside
UI/session state and are recreated by domain services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, MutableMapping

from core.application_state import ApplicationContext, ApplicationStateController
from core.workspace_session import (
    SESSION_ACTIVE_PLOT_KEY,
    SESSION_ACTIVE_REPORT_KEY,
    SESSION_SELECTED_INTERVALS_KEY,
)
from core.workbench_shell import WorkbenchInteractionState, WorkbenchShellModel
from core.workbench_tools import WORKBENCH_ACTIVE_TOOL_KEY

WORKBENCH_SELECTION_KEY = "workbench_selection"
WORKBENCH_RENDERER_STATE_KEY = "workbench_renderer_state"
WORKBENCH_LIFECYCLE_STATE_KEY = "workbench_lifecycle_state"
WORKBENCH_LIFECYCLE_OPENED_SESSION_KEY = "workbench_lifecycle_opened_session"

SelectionTarget = str


@dataclass(frozen=True, slots=True)
class WorkbenchSelection:
    """Current object selection inside the Workbench.

    The service stores only references to domain objects.  A selected LAS,
    report, interval or plot is represented by a small id string so the
    Workbench can coordinate panels without becoming a calculation engine.
    """

    target: SelectionTarget = ""
    object_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "WorkbenchSelection":
        data = dict(value or {})
        return cls(
            target=str(data.get("target", "") or ""),
            object_id=str(data.get("object_id", "") or data.get("id", "") or ""),
            metadata=dict(data.get("metadata", {}) or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "object_id": self.object_id,
            "metadata": dict(self.metadata),
        }

    def is_empty(self) -> bool:
        return not bool(self.target and self.object_id)


class WorkbenchSelectionService:
    """Central selection boundary for Workbench panels and renderers."""

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state
        self.state_controller = ApplicationStateController(state)

    def current(self) -> WorkbenchSelection:
        return WorkbenchSelection.from_dict(self.state.get(WORKBENCH_SELECTION_KEY, {}))

    def select(self, target: str, object_id: str, metadata: dict[str, Any] | None = None) -> WorkbenchSelection:
        clean_target = str(target or "").strip()
        clean_object_id = str(object_id or "").strip()
        if not clean_target:
            raise ValueError("Selection target must not be empty.")
        if not clean_object_id:
            raise ValueError("Selection object id must not be empty.")
        selection = WorkbenchSelection(clean_target, clean_object_id, dict(metadata or {}))
        self.state[WORKBENCH_SELECTION_KEY] = selection.to_dict()
        self._mirror_domain_selection(selection)
        self.state_controller.publish_event(
            "workbench.selection.changed",
            selection.to_dict(),
            source="WorkbenchSelectionService",
        )
        return selection

    def clear(self, reason: str = "selection_cleared") -> WorkbenchSelection:
        previous = self.current()
        self.state.pop(WORKBENCH_SELECTION_KEY, None)
        self.state_controller.publish_event(
            "workbench.selection.changed",
            {"target": "", "object_id": "", "previous": previous.to_dict(), "reason": str(reason or "selection_cleared")},
            source="WorkbenchSelectionService",
        )
        return WorkbenchSelection()

    def _mirror_domain_selection(self, selection: WorkbenchSelection) -> None:
        """Mirror known selections to existing lightweight session keys."""

        if selection.target == "report":
            self.state[SESSION_ACTIVE_REPORT_KEY] = selection.object_id
        elif selection.target == "plot":
            self.state[SESSION_ACTIVE_PLOT_KEY] = selection.object_id
        elif selection.target == "interval":
            existing = list(self.state.get(SESSION_SELECTED_INTERVALS_KEY, ()) or ())
            if selection.object_id not in existing:
                existing.append(selection.object_id)
            self.state[SESSION_SELECTED_INTERVALS_KEY] = existing


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value if str(item or "").strip())
    return ()


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Aggregated Workbench context consumed by controllers and renderers."""

    application: ApplicationContext
    interaction: WorkbenchInteractionState
    selection: WorkbenchSelection = field(default_factory=WorkbenchSelection)
    active_tool: str = ""
    selected_intervals: tuple[str, ...] = ()
    active_report: str = ""
    active_plot: str = ""
    renderer_state: dict[str, Any] = field(default_factory=dict)
    lifecycle_state: str = "closed"

    @classmethod
    def from_state(
        cls,
        state: MutableMapping[str, Any],
        shell: WorkbenchShellModel | None = None,
    ) -> "WorkspaceContext":
        application = ApplicationContext.from_state(state)
        interaction = shell.interaction if shell is not None else WorkbenchInteractionState()
        return cls(
            application=application,
            interaction=interaction,
            selection=WorkbenchSelectionService(state).current(),
            active_tool=str(state.get(WORKBENCH_ACTIVE_TOOL_KEY, "") or ""),
            selected_intervals=_string_tuple(state.get(SESSION_SELECTED_INTERVALS_KEY, ())),
            active_report=str(state.get(SESSION_ACTIVE_REPORT_KEY, "") or ""),
            active_plot=str(state.get(SESSION_ACTIVE_PLOT_KEY, "") or ""),
            renderer_state=dict(state.get(WORKBENCH_RENDERER_STATE_KEY, {}) or {}),
            lifecycle_state=str(state.get(WORKBENCH_LIFECYCLE_STATE_KEY, "closed") or "closed"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "application": self.application.to_dict(),
            "project": self.application.project_id,
            "well": self.application.well_id,
            "las": self.application.las_id,
            "workspace": self.application.workspace_id,
            "navigation": self.interaction.active_navigation_id,
            "dock_pane": self.interaction.active_dock_pane_id,
            "selection": self.selection.to_dict(),
            "active_tool": self.active_tool,
            "selected_intervals": list(self.selected_intervals),
            "active_report": self.active_report,
            "active_plot": self.active_plot,
            "renderer_state": dict(self.renderer_state),
            "lifecycle_state": self.lifecycle_state,
        }
