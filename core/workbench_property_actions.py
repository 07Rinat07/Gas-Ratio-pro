"""Context actions for the Workbench Properties pane.

The module is framework-neutral.  The renderer only requests an action; the
application layer consumes it on the next rerun and performs the domain
operation.  This keeps destructive repository mutations out of the renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping

from core.application_state import ApplicationStateController

WORKBENCH_PROPERTY_ACTION_REQUEST_KEY = "workbench_property_action_request"
WORKBENCH_PROPERTY_ACTION_RESULT_KEY = "workbench_property_action_result"
WORKBENCH_PROPERTY_TECHNICAL_KEY = "workbench_property_technical_details"
WORKBENCH_PROPERTY_ACTION_COMMAND_ID = "workbench.property_action.request"


@dataclass(frozen=True, slots=True)
class WorkbenchPropertyAction:
    id: str
    title: str
    destructive: bool = False
    requires_confirmation: bool = False
    navigation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "destructive": self.destructive,
            "requires_confirmation": self.requires_confirmation,
            "navigation_id": self.navigation_id,
        }


_ACTIONS: dict[str, tuple[WorkbenchPropertyAction, ...]] = {
    "project": (
        WorkbenchPropertyAction("open", "Открыть", navigation_id="nav.dashboard"),
        WorkbenchPropertyAction("technical", "Технические сведения"),
    ),
    "las": (
        WorkbenchPropertyAction("open", "Открыть LAS", navigation_id="nav.las_workspace"),
        WorkbenchPropertyAction("verify", "Проверить"),
        WorkbenchPropertyAction("archive", "Архивировать", requires_confirmation=True),
        WorkbenchPropertyAction("technical", "Технические сведения"),
    ),
    "dataset": (
        WorkbenchPropertyAction("open", "Открыть dataset", navigation_id="nav.data"),
        WorkbenchPropertyAction("verify", "Проверить"),
        WorkbenchPropertyAction("delete", "Удалить", destructive=True, requires_confirmation=True),
        WorkbenchPropertyAction("technical", "Технические сведения"),
    ),
    "calculation": (
        WorkbenchPropertyAction("open", "Открыть расчёт", navigation_id="nav.data"),
        WorkbenchPropertyAction("verify", "Проверить целостность"),
        WorkbenchPropertyAction("download", "Выгрузки", navigation_id="nav.data"),
        WorkbenchPropertyAction("delete", "Удалить", destructive=True, requires_confirmation=True),
        WorkbenchPropertyAction("technical", "Технические сведения"),
    ),
    "export": (
        WorkbenchPropertyAction("open", "Открыть экспорт", navigation_id="nav.exports"),
        WorkbenchPropertyAction("download", "Скачать", navigation_id="nav.exports"),
        WorkbenchPropertyAction("delete", "Удалить", destructive=True, requires_confirmation=True),
        WorkbenchPropertyAction("technical", "Технические сведения"),
    ),
    "report": (
        WorkbenchPropertyAction("open", "Открыть отчёт", navigation_id="nav.reports"),
        WorkbenchPropertyAction("download", "Скачать", navigation_id="nav.reports"),
        WorkbenchPropertyAction("technical", "Технические сведения"),
    ),
}


def property_actions_for(target: str) -> tuple[dict[str, Any], ...]:
    return tuple(action.to_dict() for action in _ACTIONS.get(str(target or "").strip().lower(), ()))


class WorkbenchPropertyActionService:
    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state
        self.controller = ApplicationStateController(state)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        action_id = str(payload.get("action_id") or "").strip().lower()
        target = str(payload.get("target") or "").strip().lower()
        object_id = str(payload.get("object_id") or "").strip()
        if not action_id or not target or not object_id:
            raise ValueError("Property action requires action_id, target and object_id.")
        allowed = {item["id"] for item in property_actions_for(target)}
        if action_id not in allowed:
            raise ValueError(f"Unsupported Properties action: {target}/{action_id}")
        request = {
            "action_id": action_id,
            "target": target,
            "object_id": object_id,
            "metadata": dict(payload.get("metadata", {}) or {}),
            "confirmed": bool(payload.get("confirmed", False)),
        }
        self.state[WORKBENCH_PROPERTY_ACTION_REQUEST_KEY] = request
        self.controller.publish_event("workbench.properties.action_requested", request, source="WorkbenchPropertyActionService")
        return request

    def consume(self) -> dict[str, Any] | None:
        value = self.state.pop(WORKBENCH_PROPERTY_ACTION_REQUEST_KEY, None)
        return dict(value) if isinstance(value, dict) else None

    def set_result(self, *, success: bool, message: str, action_id: str = "") -> None:
        self.state[WORKBENCH_PROPERTY_ACTION_RESULT_KEY] = {
            "success": bool(success), "message": str(message), "action_id": str(action_id)
        }

    def result(self) -> dict[str, Any] | None:
        value = self.state.get(WORKBENCH_PROPERTY_ACTION_RESULT_KEY)
        return dict(value) if isinstance(value, dict) else None
