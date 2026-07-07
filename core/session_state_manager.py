"""Session-state cleanup service for workspace boundary changes.

The service is intentionally framework-neutral: Streamlit's ``st.session_state``
can be passed directly because it behaves like a mutable mapping, but tests can
use a plain dictionary. It implements the Roadmap v4 rule that temporary LAS,
plot, calculation, interpretation and marker state must be cleared when the
active project, well or LAS changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, MutableMapping, Sequence

SESSION_STATE_MANAGER_SCHEMA = "gas-ratio-pro/session-state-manager/v1"

DEFAULT_TRANSIENT_PREFIXES = (
    "las_",
    "plot_",
    "correlation_",
    "interpretation_",
    "calculation_",
    "diagnostic_",
    "validator_",
    "ascii_",
    "curve_",
    "marker_",
    "temporary_",
    "preview_",
)

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
)

DEFAULT_PRESERVED_KEYS = (
    "user_settings",
    "workspace_settings",
    "theme",
    "language",
    "license_status",
    "eula_accepted",
)


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


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _matches_transient_key(key: str, prefixes: Sequence[str], explicit_keys: Sequence[str]) -> bool:
    normalized = str(key)
    return normalized in explicit_keys or any(normalized.startswith(prefix) for prefix in prefixes)


def clear_transient_session_state(
    state: MutableMapping[str, Any],
    *,
    reason: str,
    project_id: str = "",
    well_id: str = "",
    las_id: str = "",
    transient_prefixes: Sequence[str] = DEFAULT_TRANSIENT_PREFIXES,
    transient_keys: Sequence[str] = DEFAULT_TRANSIENT_KEYS,
    preserve_keys: Sequence[str] = DEFAULT_PRESERVED_KEYS,
) -> SessionCleanupResult:
    """Remove temporary analytical state while keeping global user settings."""

    preserved = set(str(key) for key in preserve_keys)
    cleared: list[str] = []
    retained: list[str] = []

    for key in list(state.keys()):
        key_text = str(key)
        if key_text in preserved:
            retained.append(key_text)
            continue
        if _matches_transient_key(key_text, transient_prefixes, transient_keys):
            cleared.append(key_text)
            del state[key]
        else:
            retained.append(key_text)

    state["active_project_id"] = project_id
    state["active_well_id"] = well_id
    state["active_las_id"] = las_id
    state["last_session_cleanup"] = {
        "reason": reason,
        "timestamp": _timestamp_utc(),
        "cleared_keys": list(cleared),
    }

    return SessionCleanupResult(
        reason=reason,
        cleared_keys=tuple(sorted(cleared)),
        preserved_keys=tuple(sorted(retained)),
        active_context={"project_id": project_id, "well_id": well_id, "las_id": las_id},
        timestamp=state["last_session_cleanup"]["timestamp"],
    )


def clear_on_project_change(state: MutableMapping[str, Any], project_id: str) -> SessionCleanupResult:
    """Clear transient data when the active project changes."""

    return clear_transient_session_state(state, reason="project_changed", project_id=project_id)


def clear_on_well_change(state: MutableMapping[str, Any], project_id: str, well_id: str) -> SessionCleanupResult:
    """Clear transient data when the active well changes."""

    return clear_transient_session_state(state, reason="well_changed", project_id=project_id, well_id=well_id)


def clear_on_las_change(state: MutableMapping[str, Any], project_id: str, well_id: str, las_id: str) -> SessionCleanupResult:
    """Clear transient data when the active LAS file changes."""

    return clear_transient_session_state(state, reason="las_changed", project_id=project_id, well_id=well_id, las_id=las_id)
