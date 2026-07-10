"""Workspace persistence bridge for the renderer-neutral LAS Viewer session.

The bridge stores only the compact serialized LAS Viewer state. Raw LAS samples,
render models and cache payloads are intentionally excluded from Workspace Session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

from core.application_state import ACTIVE_LAS_ID_KEY, ACTIVE_PROJECT_ID_KEY
from core.workspace_session import SESSION_LAS_VIEWER_STATE_KEY
from services.las_viewer_session import LasViewerSession, LasViewerState


@dataclass(frozen=True, slots=True)
class LasViewerWorkspaceSessionResult:
    stored: bool
    restored: bool
    state: LasViewerState | None = None
    reason: str = ""


class LasViewerWorkspaceSessionBridge:
    """Capture and restore one LAS Viewer state through application state."""

    def __init__(self, workspace_state: MutableMapping[str, Any]) -> None:
        self._workspace_state = workspace_state

    def store(self, session: LasViewerSession) -> LasViewerWorkspaceSessionResult:
        state = session.state
        self._workspace_state[SESSION_LAS_VIEWER_STATE_KEY] = state.to_dict()
        return LasViewerWorkspaceSessionResult(stored=True, restored=False, state=state)

    def restore(self, *, require_active_context: bool = True) -> LasViewerWorkspaceSessionResult:
        raw = self._workspace_state.get(SESSION_LAS_VIEWER_STATE_KEY)
        if not isinstance(raw, Mapping) or not raw:
            return LasViewerWorkspaceSessionResult(False, False, reason="missing_state")

        try:
            state = LasViewerState.from_dict(raw)
        except (TypeError, ValueError, KeyError):
            return LasViewerWorkspaceSessionResult(False, False, reason="invalid_state")

        if require_active_context:
            active_project = str(self._workspace_state.get(ACTIVE_PROJECT_ID_KEY, "") or "").strip()
            active_las = str(self._workspace_state.get(ACTIVE_LAS_ID_KEY, "") or "").strip()
            if active_project and state.project_id and active_project != state.project_id:
                return LasViewerWorkspaceSessionResult(False, False, state=state, reason="project_mismatch")
            if active_las and active_las != state.las_id:
                return LasViewerWorkspaceSessionResult(False, False, state=state, reason="las_mismatch")

        session = LasViewerSession.from_state(state)
        restored = session.state
        return LasViewerWorkspaceSessionResult(False, True, state=restored)

    def restore_session(self, *, require_active_context: bool = True) -> LasViewerSession | None:
        result = self.restore(require_active_context=require_active_context)
        if not result.restored or result.state is None:
            return None
        return LasViewerSession.from_state(result.state)

    def clear(self) -> bool:
        return self._workspace_state.pop(SESSION_LAS_VIEWER_STATE_KEY, None) is not None
