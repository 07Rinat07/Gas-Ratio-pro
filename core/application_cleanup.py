"""Centralized application cleanup helpers.

The Streamlit UI used to clear LAS/workspace data by directly iterating over
``st.session_state`` keys in ``app/streamlit_app.py``.  Sprint 1 moves this
responsibility into the application core: UI code should request a cleanup and
refresh, while the core decides which transient keys are invalidated and records
an event for diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, MutableMapping

from core.application_state import ApplicationStateController
from core.session_state_manager import SessionCleanupResult


CacheClearer = Callable[[], None]


@dataclass(frozen=True)
class ApplicationCleanupResult:
    """Result of a UI/application cleanup operation."""

    cleanup: SessionCleanupResult
    cache_cleared: bool
    refresh_requested: bool
    reason: str

    @property
    def cleared_keys(self) -> tuple[str, ...]:
        """Session-state keys removed by the cleanup."""

        return self.cleanup.cleared_keys


class ApplicationCleanupController:
    """Single entry point for clearing derived UI/workspace state.

    The controller is intentionally framework-neutral.  It works with a plain
    mutable mapping in tests and with ``st.session_state`` in the Streamlit app.
    The optional ``cache_clearer`` callback allows the app shell to clear
    Streamlit caches without importing Streamlit into the core package.
    """

    def __init__(self, state: MutableMapping[str, Any], *, cache_clearer: CacheClearer | None = None) -> None:
        self.state = state
        self.cache_clearer = cache_clearer
        self.state_controller = ApplicationStateController(state)

    def clear_workspace_state(
        self,
        reason: str,
        *,
        source: str = "application_cleanup",
        request_refresh: bool = True,
    ) -> ApplicationCleanupResult:
        """Clear transient tables/graphs/statistics for the current context.

        Persistent context keys such as active project/well/LAS/workspace are
        preserved.  Derived keys are removed by ``SessionStateManager`` using
        the same rules as project/well/LAS/workspace transitions.
        """

        cleanup = self.state_controller.clear_current_context(reason=reason)
        cache_cleared = False
        if self.cache_clearer is not None:
            try:
                self.cache_clearer()
                cache_cleared = True
            except Exception as exc:  # pragma: no cover - defensive runtime path
                self.state_controller.publish_event(
                    "cache.clear_failed",
                    {"reason": reason, "error": str(exc)},
                    source=source,
                )

        self.state_controller.publish_event(
            "workspace.cleanup_completed",
            {
                "reason": reason,
                "cleared_keys": list(cleanup.cleared_keys),
                "cache_cleared": cache_cleared,
            },
            source=source,
        )
        if request_refresh:
            self.state_controller.request_refresh(reason, source=source)
        return ApplicationCleanupResult(
            cleanup=cleanup,
            cache_cleared=cache_cleared,
            refresh_requested=request_refresh,
            reason=reason,
        )
