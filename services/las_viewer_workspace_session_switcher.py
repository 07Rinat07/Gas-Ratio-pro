"""Safe switching and recovery for multiple LAS Viewer workspace sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from services.las_viewer_session import LasViewerSession, LasViewerState
from services.las_viewer_workspace_autosave_repository import (
    LasViewerAutosaveRepositoryRecovery,
    LasViewerWorkspaceAutosaveRepository,
)


@dataclass(frozen=True, slots=True)
class LasViewerSessionSwitchResult:
    switched: bool
    recovered: bool = False
    autosaved_previous: bool = False
    previous_state: LasViewerState | None = None
    current_state: LasViewerState | None = None
    reason: str = ""


class LasViewerWorkspaceSessionSwitcher:
    """Own the active LAS Viewer session and switch without losing state.

    The switcher autosaves the current session before activating another one.
    A failed recovery never replaces the active session.
    """

    def __init__(
        self,
        repository: LasViewerWorkspaceAutosaveRepository,
        *,
        active_session: LasViewerSession | None = None,
    ) -> None:
        self.repository = repository
        self._active_session = active_session

    @property
    def active_session(self) -> LasViewerSession | None:
        return self._active_session

    @property
    def active_state(self) -> LasViewerState | None:
        return self._active_session.state if self._active_session is not None else None

    def activate(
        self,
        session: LasViewerSession,
        *,
        autosave_previous: bool = True,
    ) -> LasViewerSessionSwitchResult:
        if not isinstance(session, LasViewerSession):
            raise TypeError("session must be LasViewerSession")

        previous = self.active_state
        target = session.state
        if previous is not None and self._same_identity(previous, target):
            self._active_session = session
            return LasViewerSessionSwitchResult(
                switched=False,
                previous_state=previous,
                current_state=target,
                reason="same_session",
            )

        saved = False
        if autosave_previous and self._active_session is not None:
            saved = self.repository.save(self._active_session).written

        self._active_session = session
        return LasViewerSessionSwitchResult(
            switched=True,
            autosaved_previous=saved,
            previous_state=previous,
            current_state=target,
        )

    def recover_and_activate(
        self,
        *,
        project_id: str = "",
        las_id: str = "",
        autosave_previous: bool = True,
    ) -> LasViewerSessionSwitchResult:
        recovery = self.repository.recover_latest(project_id=project_id, las_id=las_id)
        return self._activate_recovery(recovery, autosave_previous=autosave_previous)

    def open_or_recover(
        self,
        factory: Callable[[], LasViewerSession],
        *,
        project_id: str = "",
        las_id: str = "",
        autosave_previous: bool = True,
    ) -> LasViewerSessionSwitchResult:
        """Recover a compatible autosave or create a fresh session lazily."""
        recovery = self.repository.recover_latest(project_id=project_id, las_id=las_id)
        if recovery.recovered:
            return self._activate_recovery(recovery, autosave_previous=autosave_previous)
        session = factory()
        result = self.activate(session, autosave_previous=autosave_previous)
        return LasViewerSessionSwitchResult(
            switched=result.switched,
            recovered=False,
            autosaved_previous=result.autosaved_previous,
            previous_state=result.previous_state,
            current_state=result.current_state,
            reason="created_fresh_session",
        )

    def close(self, *, autosave: bool = True) -> LasViewerSessionSwitchResult:
        previous = self.active_state
        if self._active_session is None:
            return LasViewerSessionSwitchResult(switched=False, reason="no_active_session")
        saved = self.repository.save(self._active_session).written if autosave else False
        self._active_session = None
        return LasViewerSessionSwitchResult(
            switched=True,
            autosaved_previous=saved,
            previous_state=previous,
            current_state=None,
            reason="closed",
        )

    def _activate_recovery(
        self,
        recovery: LasViewerAutosaveRepositoryRecovery,
        *,
        autosave_previous: bool,
    ) -> LasViewerSessionSwitchResult:
        previous = self.active_state
        if not recovery.recovered or recovery.state is None:
            return LasViewerSessionSwitchResult(
                switched=False,
                previous_state=previous,
                current_state=previous,
                reason=recovery.reason or "missing_compatible_autosave",
            )
        session = LasViewerSession.from_state(recovery.state)
        result = self.activate(session, autosave_previous=autosave_previous)
        return LasViewerSessionSwitchResult(
            switched=result.switched,
            recovered=True,
            autosaved_previous=result.autosaved_previous,
            previous_state=result.previous_state,
            current_state=result.current_state,
            reason="recovered_from_backup" if recovery.used_backup else "recovered",
        )

    @staticmethod
    def _same_identity(left: LasViewerState, right: LasViewerState) -> bool:
        return left.project_id == right.project_id and left.las_id == right.las_id
