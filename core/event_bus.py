"""Small framework-neutral application event bus.

The project is moving away from ad-hoc ``st.rerun()`` calls and direct
``st.session_state`` edits spread across the UI.  This module provides a tiny
state-backed event queue that can be used with Streamlit's session state or a
plain dictionary in tests.

The bus is intentionally simple: every domain action publishes an
``ApplicationEvent`` and the UI layer may consume those events at safe render
boundaries to refresh tables, dashboards or workspaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, MutableMapping

EVENT_QUEUE_KEY = "application_event_queue"
EVENT_HISTORY_KEY = "application_event_history"
REFRESH_REQUEST_KEY = "application_refresh_request"
EVENT_HISTORY_LIMIT = 100


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ApplicationEvent:
    """A serializable application event."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "application"
    timestamp: str = field(default_factory=_utc_timestamp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "payload": dict(self.payload),
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ApplicationEvent":
        return cls(
            name=str(value.get("name", "")),
            payload=dict(value.get("payload", {}) or {}),
            source=str(value.get("source", "application") or "application"),
            timestamp=str(value.get("timestamp", "") or _utc_timestamp()),
        )


class ApplicationEventBus:
    """State-backed event bus used by controllers and Streamlit UI."""

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state

    def publish(self, name: str, payload: dict[str, Any] | None = None, *, source: str = "application") -> ApplicationEvent:
        event = ApplicationEvent(name=name, payload=dict(payload or {}), source=source)
        queue = list(self.state.get(EVENT_QUEUE_KEY, ()))
        queue.append(event.to_dict())
        self.state[EVENT_QUEUE_KEY] = queue

        history = list(self.state.get(EVENT_HISTORY_KEY, ()))
        history.append(event.to_dict())
        self.state[EVENT_HISTORY_KEY] = history[-EVENT_HISTORY_LIMIT:]
        return event

    def peek(self) -> tuple[ApplicationEvent, ...]:
        return tuple(ApplicationEvent.from_dict(item) for item in self.state.get(EVENT_QUEUE_KEY, ()) or ())

    def consume(self) -> tuple[ApplicationEvent, ...]:
        events = self.peek()
        self.state[EVENT_QUEUE_KEY] = []
        return events

    def history(self) -> tuple[ApplicationEvent, ...]:
        return tuple(ApplicationEvent.from_dict(item) for item in self.state.get(EVENT_HISTORY_KEY, ()) or ())

    def request_refresh(self, reason: str, *, source: str = "application") -> None:
        self.state[REFRESH_REQUEST_KEY] = {"reason": reason, "source": source, "timestamp": _utc_timestamp()}
        self.publish("ui.refresh_requested", {"reason": reason}, source=source)

    def consume_refresh_request(self) -> dict[str, Any] | None:
        value = self.state.pop(REFRESH_REQUEST_KEY, None)
        if not value:
            return None
        return dict(value)
