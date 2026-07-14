from __future__ import annotations

"""Command service with serializable Undo/Redo history for interpretation intervals.

The service deliberately keeps only JSON-compatible snapshots in the supplied
state mapping. Repository objects, locks, executors and other runtime services
are never stored in session state.
"""

from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_intervals import (
    DEFAULT_INTERPRETATION_ID,
    InterpretationInterval,
    InterpretationIntervalSet,
    build_interpretation_interval,
    create_interpretation_interval,
    delete_interpretation_interval,
    load_interpretation_intervals,
    save_interpretation_intervals,
    update_interpretation_interval,
)
from projects.repository import DEFAULT_PROJECTS_ROOT

INTERVAL_HISTORY_SCHEMA = "gas-ratio-pro/interpretation-interval-history/v1"
DEFAULT_HISTORY_LIMIT = 50


class InterpretationIntervalHistoryConflict(RuntimeError):
    """Raised when repository content changed outside the command service."""


def _interval_to_payload(interval: InterpretationInterval) -> dict[str, Any]:
    return asdict(interval)


def _interval_from_payload(payload: dict[str, Any]) -> InterpretationInterval:
    return build_interpretation_interval(
        interval_id=str(payload.get("id", "")),
        label=str(payload.get("label", "")),
        top=payload.get("top"),
        base=payload.get("base"),
        interval_type=str(payload.get("interval_type", "undefined")),
        color=str(payload.get("color", "#4C78A8")),
        comment=str(payload.get("comment", "")),
        source=str(payload.get("source", "manual")),
        created_at=str(payload.get("created_at", "")) or None,
        updated_at=str(payload.get("updated_at", "")) or None,
    )


def _snapshot(interval_set: InterpretationIntervalSet) -> list[dict[str, Any]]:
    return [_interval_to_payload(item) for item in interval_set.intervals]


def _snapshot_signature(snapshot: list[dict[str, Any]]) -> tuple[tuple[tuple[str, Any], ...], ...]:
    return tuple(tuple(sorted(item.items())) for item in snapshot)


def _history_key(project_id: str, well_id: str, interpretation_id: str) -> str:
    return f"interpretation_interval_history::{project_id}::{well_id}::{interpretation_id}"


class InterpretationIntervalCommandService:
    """Execute interval mutations and maintain bounded Undo/Redo stacks."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        well_id: str,
        interpretation_id: str = DEFAULT_INTERPRETATION_ID,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> None:
        if history_limit < 1:
            raise ValueError("Лимит истории должен быть не меньше 1.")
        self._state = state
        self.root = Path(root)
        self.project_id = str(project_id)
        self.well_id = str(well_id)
        self.interpretation_id = str(interpretation_id)
        self.history_limit = int(history_limit)
        self._key = _history_key(self.project_id, self.well_id, self.interpretation_id)
        self._ensure_history()

    def _ensure_history(self) -> dict[str, Any]:
        history = self._state.get(self._key)
        if not isinstance(history, dict) or history.get("schema") != INTERVAL_HISTORY_SCHEMA:
            history = {"schema": INTERVAL_HISTORY_SCHEMA, "undo": [], "redo": []}
            self._state[self._key] = history
        history.setdefault("undo", [])
        history.setdefault("redo", [])
        return history

    def _load(self) -> InterpretationIntervalSet:
        return load_interpretation_intervals(
            self.root,
            self.project_id,
            self.well_id,
            self.interpretation_id,
        )

    def _restore(self, current: InterpretationIntervalSet, snapshot: list[dict[str, Any]]) -> InterpretationIntervalSet:
        intervals = tuple(_interval_from_payload(item) for item in snapshot)
        return save_interpretation_intervals(replace(current, intervals=intervals), self.root)

    def _record(self, action: str, before: InterpretationIntervalSet, after: InterpretationIntervalSet) -> None:
        history = self._ensure_history()
        undo = list(history["undo"])
        undo.append({"action": action, "before": _snapshot(before), "after": _snapshot(after)})
        history["undo"] = undo[-self.history_limit :]
        history["redo"] = []
        self._state[self._key] = history

    def _execute(self, action: str, operation):
        before = self._load()
        result = operation()
        after = self._load()
        if _snapshot_signature(_snapshot(before)) != _snapshot_signature(_snapshot(after)):
            self._record(action, before, after)
        return result

    @property
    def can_undo(self) -> bool:
        return bool(self._ensure_history()["undo"])

    @property
    def can_redo(self) -> bool:
        return bool(self._ensure_history()["redo"])

    def history_status(self) -> dict[str, Any]:
        history = self._ensure_history()
        return {
            "can_undo": bool(history["undo"]),
            "can_redo": bool(history["redo"]),
            "undo_count": len(history["undo"]),
            "redo_count": len(history["redo"]),
            "next_undo_action": history["undo"][-1]["action"] if history["undo"] else "",
            "next_redo_action": history["redo"][-1]["action"] if history["redo"] else "",
        }

    def clear_history(self) -> None:
        self._state[self._key] = {"schema": INTERVAL_HISTORY_SCHEMA, "undo": [], "redo": []}

    def create(self, **fields: Any) -> InterpretationInterval:
        return self._execute(
            "create",
            lambda: create_interpretation_interval(
                root=self.root,
                project_id=self.project_id,
                well_id=self.well_id,
                interpretation_id=self.interpretation_id,
                **fields,
            ),
        )

    def update(self, interval_id: str, **fields: Any) -> InterpretationInterval:
        return self._execute(
            "update",
            lambda: update_interpretation_interval(
                interval_id,
                root=self.root,
                project_id=self.project_id,
                well_id=self.well_id,
                interpretation_id=self.interpretation_id,
                **fields,
            ),
        )

    def delete(self, interval_id: str) -> bool:
        return self._execute(
            "delete",
            lambda: delete_interpretation_interval(
                interval_id,
                root=self.root,
                project_id=self.project_id,
                well_id=self.well_id,
                interpretation_id=self.interpretation_id,
            ),
        )

    def replace_all(
        self,
        intervals: tuple[InterpretationInterval, ...],
        *,
        action: str = "replace_all",
    ) -> InterpretationIntervalSet:
        """Replace the complete interval set as one reversible command."""

        normalized = tuple(intervals)

        def operation() -> InterpretationIntervalSet:
            current = self._load()
            return save_interpretation_intervals(replace(current, intervals=normalized), self.root)

        return self._execute(action, operation)

    def undo(self) -> bool:
        history = self._ensure_history()
        if not history["undo"]:
            return False
        entry = history["undo"][-1]
        current = self._load()
        if _snapshot_signature(_snapshot(current)) != _snapshot_signature(entry["after"]):
            raise InterpretationIntervalHistoryConflict(
                "Интервалы изменены вне истории команд; Undo отменён для защиты данных."
            )
        self._restore(current, entry["before"])
        history["undo"] = history["undo"][:-1]
        history["redo"] = [*history["redo"], entry][-self.history_limit :]
        self._state[self._key] = history
        return True

    def redo(self) -> bool:
        history = self._ensure_history()
        if not history["redo"]:
            return False
        entry = history["redo"][-1]
        current = self._load()
        if _snapshot_signature(_snapshot(current)) != _snapshot_signature(entry["before"]):
            raise InterpretationIntervalHistoryConflict(
                "Интервалы изменены вне истории команд; Redo отменён для защиты данных."
            )
        self._restore(current, entry["after"])
        history["redo"] = history["redo"][:-1]
        history["undo"] = [*history["undo"], entry][-self.history_limit :]
        self._state[self._key] = history
        return True
