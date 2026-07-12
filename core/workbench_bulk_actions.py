"""Framework-neutral bulk actions for Workbench Data Grid selections."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping

from core.application_state import ApplicationStateController

WORKBENCH_BULK_ACTION_REQUEST_KEY = "workbench_bulk_action_request"
WORKBENCH_BULK_ACTION_RESULT_KEY = "workbench_bulk_action_result"
WORKBENCH_BULK_SELECTIONS_KEY = "workbench_bulk_selections"


@dataclass(frozen=True, slots=True)
class WorkbenchBulkAction:
    id: str
    title: str
    destructive: bool = False
    requires_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "destructive": self.destructive,
            "requires_confirmation": self.requires_confirmation,
        }


_ACTIONS: dict[str, tuple[WorkbenchBulkAction, ...]] = {
    "dataset": (
        WorkbenchBulkAction("verify", "Проверить выбранные"),
        WorkbenchBulkAction("export", "Экспортировать список"),
        WorkbenchBulkAction("delete", "Удалить выбранные", destructive=True, requires_confirmation=True),
    ),
    "calculation": (
        WorkbenchBulkAction("verify", "Проверить целостность"),
        WorkbenchBulkAction("export", "Создать ZIP-пакет"),
        WorkbenchBulkAction("delete", "Удалить выбранные", destructive=True, requires_confirmation=True),
    ),
    "export": (
        WorkbenchBulkAction("verify", "Проверить выбранные"),
        WorkbenchBulkAction("export", "Создать ZIP-пакет"),
        WorkbenchBulkAction("delete", "Удалить выбранные", destructive=True, requires_confirmation=True),
    ),
}


def bulk_actions_for(target: str) -> tuple[dict[str, Any], ...]:
    return tuple(action.to_dict() for action in _ACTIONS.get(str(target or "").strip().lower(), ()))


class WorkbenchBulkActionService:
    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state
        self.controller = ApplicationStateController(state)

    def set_selection(self, *, key: str, target: str, object_ids: list[str] | tuple[str, ...], metadata: dict[str, Any] | None = None) -> None:
        selections = dict(self.state.get(WORKBENCH_BULK_SELECTIONS_KEY, {}) or {})
        selections[str(key)] = {
            "target": str(target),
            "object_ids": tuple(dict.fromkeys(str(item) for item in object_ids if str(item).strip())),
            "metadata": dict(metadata or {}),
        }
        self.state[WORKBENCH_BULK_SELECTIONS_KEY] = selections

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = str(payload.get("target") or "").strip().lower()
        action_id = str(payload.get("action_id") or "").strip().lower()
        object_ids = tuple(dict.fromkeys(str(item) for item in payload.get("object_ids", ()) if str(item).strip()))
        allowed = {item["id"] for item in bulk_actions_for(target)}
        if not target or action_id not in allowed or not object_ids:
            raise ValueError("Bulk action requires a supported target, action and at least one object.")
        request = {
            "target": target,
            "action_id": action_id,
            "object_ids": object_ids,
            "metadata": dict(payload.get("metadata", {}) or {}),
            "confirmed": bool(payload.get("confirmed", False)),
        }
        self.state[WORKBENCH_BULK_ACTION_REQUEST_KEY] = request
        self.controller.publish_event("workbench.bulk.action_requested", request, source="WorkbenchBulkActionService")
        return request

    def consume(self) -> dict[str, Any] | None:
        value = self.state.pop(WORKBENCH_BULK_ACTION_REQUEST_KEY, None)
        return dict(value) if isinstance(value, dict) else None

    def set_result(self, *, success: bool, message: str, action_id: str = "", export_id: str = "") -> None:
        self.state[WORKBENCH_BULK_ACTION_RESULT_KEY] = {
            "success": bool(success),
            "message": str(message),
            "action_id": str(action_id),
            "export_id": str(export_id),
        }

    def result(self) -> dict[str, Any] | None:
        value = self.state.get(WORKBENCH_BULK_ACTION_RESULT_KEY)
        return dict(value) if isinstance(value, dict) else None
