"""Session-state cleanup service for workspace boundary changes.

The service is framework-neutral: Streamlit's ``st.session_state`` can be passed
because it behaves like a mutable mapping, while tests can use a plain dict.

Roadmap v5 rule: when project, well, LAS file or workspace changes, all derived
UI state must be invalidated. This includes not only charts and calculations,
but also tables, statistics, dashboards, previews, temporary dataframes and
workspace-local selections. Global user settings are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, MutableMapping, Sequence

SESSION_STATE_MANAGER_SCHEMA = "gas-ratio-pro/session-state-manager/v2"

# Prefixes that represent derived UI/analytical state. These values are
# intentionally broad because stale tables/statistics are more dangerous than a
# harmless recomputation on the next render.
DEFAULT_TRANSIENT_PREFIXES = (
    "las_",
    "las_editor_",
    "plot_",
    "plot_studio_",
    "correlation_",
    "interpretation_",
    "calculation_",
    "diagnostic_",
    "diagnostics_",
    "validator_",
    "ascii_",
    "curve_",
    "marker_",
    "temporary_",
    "temp_",
    "preview_",
    "table_",
    "tables_",
    "stats_",
    "stat_",
    "statistics_",
    "summary_",
    "dashboard_",
    "report_",
    "export_",
    "modeling_",
    "geological_",
    "petrophysics_",
    "workspace_local_",
)

# Explicit keys used by the current Streamlit application and backend modules.
# They do not all share a safe prefix, therefore they must be listed directly.
DEFAULT_TRANSIENT_KEYS = (
    "current_las_data",
    "current_las_header",
    "current_las_path",
    "current_well_data",
    "active_dataframe",
    "active_plot",
    "active_markers",
    "selected_curves",
    "depth_repair_preview",
    "processing_pipeline_preview",
    "project_session_sheets",
    "project_session_summary",
    "project_session_project_id",
    "interpretation_session_data",
    "interpretation_session_source",
    "last_rendered_table",
    "last_rendered_statistics",
    "active_statistics",
    "active_summary_table",
    "active_quality_table",
    "active_diagnostics_table",
    "active_validation_table",
    "active_report_preview",
)

# Keys that may remain across workspace boundaries. These are user/global
# settings, not derived data.
DEFAULT_PRESERVED_KEYS = (
    "user_settings",
    "workspace_settings",
    "theme",
    "language",
    "license_status",
    "eula_accepted",
    "active_project_id",
    "active_well_id",
    "active_las_id",
    "active_workspace_id",
    "last_session_cleanup",
)

CONTEXT_KEYS = {
    "project": "active_project_id",
    "well": "active_well_id",
    "las": "active_las_id",
    "workspace": "active_workspace_id",
}


@dataclass(frozen=True)
class SessionCleanupResult:
    """Result of clearing transient state after a workspace boundary change."""

    reason: str
    cleared_keys: tuple[str, ...]
    preserved_keys: tuple[str, ...]
    active_context: dict[str, str]
    timestamp: str
    schema: str = SESSION_STATE_MANAGER_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "cleared_keys": list(self.cleared_keys),
            "preserved_keys": list(self.preserved_keys),
            "active_context": dict(self.active_context),
        }


@dataclass(frozen=True)
class SessionContext:
    """Logical application context used to detect stale UI state."""

    project_id: str = ""
    well_id: str = ""
    las_id: str = ""
    workspace_id: str = ""

    def to_active_context(self) -> dict[str, str]:
        return {
            "project_id": self.project_id,
            "well_id": self.well_id,
            "las_id": self.las_id,
            "workspace_id": self.workspace_id,
        }

    @classmethod
    def from_state(cls, state: MutableMapping[str, Any]) -> "SessionContext":
        return cls(
            project_id=str(state.get("active_project_id", "") or ""),
            well_id=str(state.get("active_well_id", "") or ""),
            las_id=str(state.get("active_las_id", "") or ""),
            workspace_id=str(state.get("active_workspace_id", "") or ""),
        )


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _matches_transient_key(key: str, prefixes: Sequence[str], explicit_keys: Sequence[str]) -> bool:
    normalized = str(key)
    return normalized in explicit_keys or any(normalized.startswith(prefix) for prefix in prefixes)


def is_transient_session_key(
    key: str,
    *,
    transient_prefixes: Sequence[str] = DEFAULT_TRANSIENT_PREFIXES,
    transient_keys: Sequence[str] = DEFAULT_TRANSIENT_KEYS,
    preserve_keys: Sequence[str] = DEFAULT_PRESERVED_KEYS,
) -> bool:
    """Return True when a key contains derived state that must be invalidated."""

    key_text = str(key)
    if key_text in set(str(item) for item in preserve_keys):
        return False
    return _matches_transient_key(key_text, transient_prefixes, transient_keys)


def clear_transient_session_state(
    state: MutableMapping[str, Any],
    *,
    reason: str,
    project_id: str = "",
    well_id: str = "",
    las_id: str = "",
    workspace_id: str = "",
    transient_prefixes: Sequence[str] = DEFAULT_TRANSIENT_PREFIXES,
    transient_keys: Sequence[str] = DEFAULT_TRANSIENT_KEYS,
    preserve_keys: Sequence[str] = DEFAULT_PRESERVED_KEYS,
) -> SessionCleanupResult:
    """Remove derived tables/statistics/previews while keeping global settings."""

    cleared: list[str] = []
    retained: list[str] = []

    for key in list(state.keys()):
        key_text = str(key)
        if is_transient_session_key(
            key_text,
            transient_prefixes=transient_prefixes,
            transient_keys=transient_keys,
            preserve_keys=preserve_keys,
        ):
            cleared.append(key_text)
            del state[key]
        else:
            retained.append(key_text)

    state["active_project_id"] = project_id
    state["active_well_id"] = well_id
    state["active_las_id"] = las_id
    state["active_workspace_id"] = workspace_id
    state["last_session_cleanup"] = {
        "reason": reason,
        "timestamp": _timestamp_utc(),
        "cleared_keys": list(sorted(cleared)),
        "active_context": {
            "project_id": project_id,
            "well_id": well_id,
            "las_id": las_id,
            "workspace_id": workspace_id,
        },
    }

    return SessionCleanupResult(
        reason=reason,
        cleared_keys=tuple(sorted(cleared)),
        preserved_keys=tuple(sorted(retained)),
        active_context={
            "project_id": project_id,
            "well_id": well_id,
            "las_id": las_id,
            "workspace_id": workspace_id,
        },
        timestamp=state["last_session_cleanup"]["timestamp"],
    )


def clear_on_project_change(state: MutableMapping[str, Any], project_id: str) -> SessionCleanupResult:
    """Clear derived data when the active project changes."""

    return clear_transient_session_state(state, reason="project_changed", project_id=project_id)


def clear_on_well_change(state: MutableMapping[str, Any], project_id: str, well_id: str) -> SessionCleanupResult:
    """Clear derived data when the active well changes."""

    return clear_transient_session_state(state, reason="well_changed", project_id=project_id, well_id=well_id)


def clear_on_las_change(state: MutableMapping[str, Any], project_id: str, well_id: str, las_id: str) -> SessionCleanupResult:
    """Clear derived data when the active LAS file changes."""

    return clear_transient_session_state(state, reason="las_changed", project_id=project_id, well_id=well_id, las_id=las_id)


def clear_on_workspace_change(
    state: MutableMapping[str, Any],
    project_id: str,
    well_id: str,
    las_id: str,
    workspace_id: str,
) -> SessionCleanupResult:
    """Clear workspace-local data when the user switches major workspace."""

    return clear_transient_session_state(
        state,
        reason="workspace_changed",
        project_id=project_id,
        well_id=well_id,
        las_id=las_id,
        workspace_id=workspace_id,
    )


def ensure_session_context(
    state: MutableMapping[str, Any],
    *,
    project_id: str = "",
    well_id: str = "",
    las_id: str = "",
    workspace_id: str = "",
) -> SessionCleanupResult | None:
    """Clear derived state only when the logical context actually changed.

    This helper is intended for the application shell. It prevents stale tables
    and statistics from surviving when a new project/well/LAS/workspace is
    opened, while avoiding unnecessary resets during ordinary rerenders.
    """

    previous = SessionContext.from_state(state)
    current = SessionContext(project_id, well_id, las_id, workspace_id)

    if previous == current:
        return None

    if previous.project_id != current.project_id:
        reason = "project_changed"
    elif previous.well_id != current.well_id:
        reason = "well_changed"
    elif previous.las_id != current.las_id:
        reason = "las_changed"
    else:
        reason = "workspace_changed"

    return clear_transient_session_state(
        state,
        reason=reason,
        project_id=current.project_id,
        well_id=current.well_id,
        las_id=current.las_id,
        workspace_id=current.workspace_id,
    )
