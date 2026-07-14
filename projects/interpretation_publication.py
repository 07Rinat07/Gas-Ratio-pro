from __future__ import annotations

"""Persistent approval and publication workflow for one interpretation.

The workflow stores only JSON-compatible metadata. Approved and published
interpretations are read-only for interval mutations until they are reopened.
Publication is tied to an existing revision whose state token must match the
current workspace state, preventing publication of stale content.
"""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from projects.interpretation_intervals import _safe_interpretation_id
from projects.interpretation_access import (
    InterpretationActor,
    PERMISSION_APPROVE,
    PERMISSION_PUBLISH,
    PERMISSION_REOPEN,
    PERMISSION_RETURN,
    PERMISSION_SUBMIT,
    PERMISSION_UNPUBLISH,
    require_permission,
)
from projects.interpretation_revisions import InterpretationRevisionRepository
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

WORKFLOW_SCHEMA = "gas-ratio-pro/interpretation-publication/v1"
WORKFLOW_DIR_NAME = ".workflow"
WORKFLOW_FILE_NAME = "publication.json"
STATUSES = ("draft", "in_review", "approved", "published")
LOCKED_STATUSES = frozenset({"approved", "published"})
MAX_COMMENT_LENGTH = 1200


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_comment(value: Any) -> str:
    clean = str(value or "").strip()
    if len(clean) > MAX_COMMENT_LENGTH:
        raise ValueError(f"Комментарий: максимум {MAX_COMMENT_LENGTH} символов.")
    return clean


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class InterpretationPublicationEvent:
    id: str
    action: str
    from_status: str
    to_status: str
    comment: str
    created_at: str
    revision_id: str = ""
    actor_id: str = ""
    actor_name: str = ""
    actor_role: str = ""


@dataclass(frozen=True)
class InterpretationPublicationState:
    status: str = "draft"
    updated_at: str = ""
    published_revision_id: str = ""
    events: tuple[InterpretationPublicationEvent, ...] = ()

    @property
    def is_locked(self) -> bool:
        return self.status in LOCKED_STATUSES


class InterpretationPublicationRepository:
    def __init__(self, *, root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str, well_id: str, interpretation_id: str) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self.well_id = safe_well_id(well_id)
        self.interpretation_id = _safe_interpretation_id(interpretation_id)
        self.workspace_dir = self.root / self.project_id / "wells" / self.well_id / "interpretations" / self.interpretation_id
        self.path = self.workspace_dir / WORKFLOW_DIR_NAME / WORKFLOW_FILE_NAME

    def get(self) -> InterpretationPublicationState:
        if not self.path.exists():
            return InterpretationPublicationState(status="draft", updated_at="")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            raise ValueError("Файл статуса интерпретации повреждён.")
        if not isinstance(payload, Mapping) or payload.get("schema") != WORKFLOW_SCHEMA:
            raise ValueError("Неподдерживаемая схема статуса интерпретации.")
        status = str(payload.get("status", "draft"))
        if status not in STATUSES:
            raise ValueError("Некорректный статус интерпретации.")
        events: list[InterpretationPublicationEvent] = []
        for row in payload.get("events", []):
            if not isinstance(row, Mapping):
                continue
            events.append(InterpretationPublicationEvent(
                id=str(row.get("id", "")), action=str(row.get("action", "")),
                from_status=str(row.get("from_status", "")), to_status=str(row.get("to_status", "")),
                comment=str(row.get("comment", "")), created_at=str(row.get("created_at", "")),
                revision_id=str(row.get("revision_id", "")),
                actor_id=str(row.get("actor_id", "")), actor_name=str(row.get("actor_name", "")),
                actor_role=str(row.get("actor_role", "")),
            ))
        return InterpretationPublicationState(
            status=status,
            updated_at=str(payload.get("updated_at", "")),
            published_revision_id=str(payload.get("published_revision_id", "")),
            events=tuple(events),
        )

    def transition(self, *, to_status: str, action: str, comment: str = "", revision_id: str = "", actor: InterpretationActor | None = None) -> InterpretationPublicationState:
        target = str(to_status)
        if target not in STATUSES:
            raise ValueError("Некорректный целевой статус интерпретации.")
        current = self.get()
        current_actor = actor or InterpretationActor()
        event = InterpretationPublicationEvent(
            id=str(uuid4()), action=str(action), from_status=current.status, to_status=target,
            comment=_clean_comment(comment), created_at=_utc_now(), revision_id=str(revision_id or ""),
            actor_id=current_actor.id, actor_name=current_actor.name, actor_role=current_actor.role,
        )
        state = InterpretationPublicationState(
            status=target,
            updated_at=event.created_at,
            published_revision_id=str(revision_id or "") if target == "published" else "",
            events=tuple((*current.events, event)[-200:]),
        )
        _atomic_json_write(self.path, {
            "schema": WORKFLOW_SCHEMA,
            "project_id": self.project_id,
            "well_id": self.well_id,
            "interpretation_id": self.interpretation_id,
            "status": state.status,
            "updated_at": state.updated_at,
            "published_revision_id": state.published_revision_id,
            "events": [asdict(item) for item in state.events],
        })
        return state


class InterpretationPublicationService:
    def __init__(self, *, root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str, well_id: str, interpretation_id: str, actor: InterpretationActor | None = None) -> None:
        self.repository = InterpretationPublicationRepository(root=root, project_id=project_id, well_id=well_id, interpretation_id=interpretation_id)
        self.revisions = InterpretationRevisionRepository(root=root, project_id=project_id, well_id=well_id, interpretation_id=interpretation_id)
        self.actor = actor or InterpretationActor()

    def state(self) -> InterpretationPublicationState:
        return self.repository.get()

    def submit_for_review(self, *, comment: str = "") -> InterpretationPublicationState:
        self._require("draft")
        require_permission(self.actor, PERMISSION_SUBMIT)
        return self.repository.transition(to_status="in_review", action="submit_for_review", comment=comment, actor=self.actor)

    def return_to_draft(self, *, comment: str = "") -> InterpretationPublicationState:
        self._require("in_review")
        require_permission(self.actor, PERMISSION_RETURN)
        return self.repository.transition(to_status="draft", action="return_to_draft", comment=comment, actor=self.actor)

    def approve(self, *, comment: str = "") -> InterpretationPublicationState:
        self._require("in_review")
        require_permission(self.actor, PERMISSION_APPROVE)
        return self.repository.transition(to_status="approved", action="approve", comment=comment, actor=self.actor)

    def reopen(self, *, comment: str = "") -> InterpretationPublicationState:
        self._require("approved")
        require_permission(self.actor, PERMISSION_REOPEN)
        return self.repository.transition(to_status="draft", action="reopen", comment=comment, actor=self.actor)

    def publish(self, *, revision_id: str, comment: str = "") -> InterpretationPublicationState:
        self._require("approved")
        require_permission(self.actor, PERMISSION_PUBLISH)
        revision = self.revisions.get(revision_id)
        if revision.state_token != self.revisions.current_state_token():
            raise ValueError("Выбранная ревизия не соответствует текущему состоянию интерпретации.")
        return self.repository.transition(to_status="published", action="publish", comment=comment, revision_id=revision.id, actor=self.actor)

    def unpublish(self, *, comment: str = "") -> InterpretationPublicationState:
        self._require("published")
        require_permission(self.actor, PERMISSION_UNPUBLISH)
        return self.repository.transition(to_status="approved", action="unpublish", comment=comment, actor=self.actor)

    def assert_editable(self) -> None:
        state = self.state()
        if state.is_locked:
            raise ValueError("Интерпретация утверждена или опубликована и доступна только для чтения.")

    def _require(self, expected: str) -> None:
        actual = self.state().status
        if actual != expected:
            raise ValueError(f"Операция недоступна для статуса «{actual}».")
