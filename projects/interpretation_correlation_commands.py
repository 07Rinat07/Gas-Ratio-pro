from __future__ import annotations

"""Serializable Undo/Redo command layer for correlation workspaces."""

from dataclasses import asdict
from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_correlation import (
    CorrelationEndpoint,
    CorrelationTie,
    CorrelationWorkspace,
    CorrelationWorkspaceRepository,
    CorrelationWorkspaceService,
    _atomic_write,
    _utc_now,
)
from projects.repository import DEFAULT_PROJECTS_ROOT

CORRELATION_HISTORY_SCHEMA = "gas-ratio-pro/interpretation-correlation-history/v1"
DEFAULT_HISTORY_LIMIT = 50
CORRELATION_JOURNAL_SCHEMA = "gas-ratio-pro/interpretation-correlation-journal/v1"
DEFAULT_JOURNAL_LIMIT = 200


class CorrelationHistoryConflict(RuntimeError):
    """Raised when workspace content changed outside the command history."""


def _history_key(project_id: str, workspace_id: str) -> str:
    return f"interpretation_correlation_history::{project_id}::{workspace_id}"


def _snapshot(workspace: CorrelationWorkspace) -> dict[str, Any]:
    return asdict(workspace)


class CorrelationOperationJournal:
    """Small persistent audit journal without workspace snapshots or runtime objects."""

    def __init__(self, repository: CorrelationWorkspaceRepository, workspace_id: str, *, limit: int = DEFAULT_JOURNAL_LIMIT) -> None:
        self.repository = repository
        self.workspace_id = str(workspace_id)
        self.limit = max(1, int(limit))
        self.path = repository.directory / self.workspace_id / "operations.json"

    def list(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        import json
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return ()
        if payload.get("schema") != CORRELATION_JOURNAL_SCHEMA:
            return ()
        rows = payload.get("operations", [])
        return tuple(dict(item) for item in rows if isinstance(item, dict))

    def append(self, *, action: str, before: CorrelationWorkspace, after: CorrelationWorkspace) -> None:
        rows = list(self.list())
        before_ids = {item.id for item in before.ties}
        after_ids = {item.id for item in after.ties}
        rows.append({
            "timestamp": _utc_now(),
            "action": str(action),
            "before_token": before.state_token,
            "after_token": after.state_token,
            "tie_count_before": len(before.ties),
            "tie_count_after": len(after.ties),
            "added_tie_ids": sorted(after_ids - before_ids),
            "removed_tie_ids": sorted(before_ids - after_ids),
        })
        _atomic_write(self.path, {
            "schema": CORRELATION_JOURNAL_SCHEMA,
            "workspace_id": self.workspace_id,
            "operations": rows[-self.limit :],
        })


class CorrelationWorkspaceCommandService:
    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        workspace_id: str,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> None:
        if history_limit < 1:
            raise ValueError("Лимит истории должен быть не меньше 1.")
        self.state = state
        self.root = Path(root)
        self.project_id = str(project_id)
        self.workspace_id = str(workspace_id)
        self.history_limit = int(history_limit)
        self.repository = CorrelationWorkspaceRepository(root=root, project_id=project_id)
        self.service = CorrelationWorkspaceService(root=root, project_id=project_id, workspace_id=workspace_id)
        self.journal = CorrelationOperationJournal(self.repository, self.workspace_id)
        self.key = _history_key(self.project_id, self.workspace_id)
        self._history()

    def _history(self) -> dict[str, Any]:
        history = self.state.get(self.key)
        if not isinstance(history, dict) or history.get("schema") != CORRELATION_HISTORY_SCHEMA:
            history = {"schema": CORRELATION_HISTORY_SCHEMA, "undo": [], "redo": []}
            self.state[self.key] = history
        history.setdefault("undo", [])
        history.setdefault("redo", [])
        return history

    def _record(self, action: str, before: CorrelationWorkspace, after: CorrelationWorkspace) -> None:
        history = self._history()
        undo = list(history["undo"])
        undo.append({"action": action, "before": _snapshot(before), "after": _snapshot(after)})
        history["undo"] = undo[-self.history_limit :]
        history["redo"] = []
        self.state[self.key] = history
        self.journal.append(action=action, before=before, after=after)

    def _execute(self, action: str, operation):
        before = self.repository.get(self.workspace_id)
        after = operation(before)
        if before.state_token != after.state_token:
            self._record(action, before, after)
        return after

    def _restore(self, snapshot: dict[str, Any], expected_token: str) -> CorrelationWorkspace:
        current = self.repository.get(self.workspace_id)
        if current.state_token != expected_token:
            raise CorrelationHistoryConflict("Корреляционный проект изменён вне истории команд; операция отменена.")
        restored = self.repository._parse({"schema": "gas-ratio-pro/interpretation-correlation/v1", **snapshot})
        return self.repository.save(restored, expected_state_token=current.state_token, preserve_updated_at=True)

    @property
    def can_undo(self) -> bool:
        return bool(self._history()["undo"])

    @property
    def can_redo(self) -> bool:
        return bool(self._history()["redo"])

    def history_status(self) -> dict[str, Any]:
        history = self._history()
        return {
            "can_undo": bool(history["undo"]),
            "can_redo": bool(history["redo"]),
            "undo_count": len(history["undo"]),
            "redo_count": len(history["redo"]),
            "next_undo_action": history["undo"][-1]["action"] if history["undo"] else "",
            "next_redo_action": history["redo"][-1]["action"] if history["redo"] else "",
        }

    def add_tie(self, *, left: CorrelationEndpoint, right: CorrelationEndpoint, **fields: Any) -> CorrelationWorkspace:
        return self._execute("add_tie", lambda before: self.service.add_tie(
            left=left, right=right, expected_state_token=before.state_token, **fields
        ))

    def add_ties(self, ties: tuple[CorrelationTie, ...]) -> CorrelationWorkspace:
        return self._execute("add_suggested_ties", lambda before: self.service.add_ties(
            ties, expected_state_token=before.state_token
        ))

    def update_tie(self, tie_id: str, **fields: Any) -> CorrelationWorkspace:
        return self._execute("update_tie", lambda before: self.service.update_tie(
            tie_id, expected_state_token=before.state_token, **fields
        ))

    def delete_tie(self, tie_id: str) -> CorrelationWorkspace:
        return self._execute("delete_tie", lambda before: self.service.delete_tie(
            tie_id, expected_state_token=before.state_token
        ))

    def delete_ties(self, tie_ids: tuple[str, ...]) -> CorrelationWorkspace:
        return self._execute("delete_ties", lambda before: self.service.delete_ties(
            tie_ids, expected_state_token=before.state_token
        ))

    def undo(self) -> bool:
        history = self._history()
        if not history["undo"]:
            return False
        entry = history["undo"][-1]
        current = self.repository.get(self.workspace_id)
        expected_after = self.repository._parse({"schema": "gas-ratio-pro/interpretation-correlation/v1", **entry["after"]})
        if current.state_token != expected_after.state_token:
            raise CorrelationHistoryConflict("Корреляционный проект изменён вне истории команд; Undo отменён.")
        self._restore(entry["before"], current.state_token)
        history["undo"] = history["undo"][:-1]
        history["redo"] = [*history["redo"], entry][-self.history_limit :]
        self.state[self.key] = history
        return True

    def redo(self) -> bool:
        history = self._history()
        if not history["redo"]:
            return False
        entry = history["redo"][-1]
        current = self.repository.get(self.workspace_id)
        expected_before = self.repository._parse({"schema": "gas-ratio-pro/interpretation-correlation/v1", **entry["before"]})
        if current.state_token != expected_before.state_token:
            raise CorrelationHistoryConflict("Корреляционный проект изменён вне истории команд; Redo отменён.")
        self._restore(entry["after"], current.state_token)
        history["redo"] = history["redo"][:-1]
        history["undo"] = [*history["undo"], entry][-self.history_limit :]
        self.state[self.key] = history
        return True
