"""Application runtime helpers for Streamlit-safe refresh and pending transitions.

This module is the next step after introducing ``ApplicationStateController`` and
``ApplicationEventBus``.  It keeps Streamlit-specific rerun intent out of domain
services and gives the UI shell a single place to process queued context changes.

The runtime itself does not import Streamlit.  The Streamlit app can call
``request_refresh`` and then decide whether to call ``st.rerun()`` at a safe UI
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping

from core.application_state import ApplicationStateController, StateTransition


@dataclass(frozen=True)
class RuntimeCycleResult:
    """Result of processing queued application transitions."""

    transitions: tuple[StateTransition, ...]
    refresh_requested: bool
    refresh_reason: str = ""

    @property
    def changed(self) -> bool:
        """Whether at least one pending context transition changed state."""

        return any(transition.changed for transition in self.transitions)


class ApplicationRuntimeController:
    """Coordinates pending state transitions and UI refresh requests.

    The class is deliberately framework-neutral so it can be tested with a
    dictionary and used by Streamlit via ``st.session_state``.
    """

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state
        self.state_controller = ApplicationStateController(state)

    def process_pending_transitions(self) -> tuple[StateTransition, ...]:
        """Apply pending project/well/LAS/workspace changes in dependency order."""

        transitions: list[StateTransition] = []
        for transition in (
            self.state_controller.consume_pending_project_activation(),
            self.state_controller.consume_pending_well_activation(),
            self.state_controller.consume_pending_las_activation(),
            self.state_controller.consume_pending_workspace_activation(),
        ):
            if transition is not None:
                transitions.append(transition)
        return tuple(transitions)

    def request_refresh(self, reason: str, *, source: str = "application_runtime") -> None:
        """Request one UI refresh through the central event bus."""

        self.state_controller.request_refresh(reason, source=source)

    def consume_refresh_request(self) -> dict[str, Any] | None:
        """Return and clear one pending UI refresh request."""

        return self.state_controller.consume_refresh_request()

    def run_cycle(self) -> RuntimeCycleResult:
        """Process pending transitions and return refresh intent for the UI shell."""

        transitions = self.process_pending_transitions()
        refresh = self.consume_refresh_request()
        return RuntimeCycleResult(
            transitions=transitions,
            refresh_requested=bool(refresh),
            refresh_reason=str((refresh or {}).get("reason", "") or ""),
        )
