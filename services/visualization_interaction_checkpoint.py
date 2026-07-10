"""Serializable checkpoints for fast visualization interaction restoration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from services.visualization_interaction_journal import VisualizationInteractionJournal
from services.visualization_interaction_session import (
    InteractionSessionState,
    VisualizationInteractionSession,
)


@dataclass(frozen=True, slots=True)
class InteractionCheckpoint:
    """Compact state checkpoint associated with a journal sequence position."""

    state: InteractionSessionState
    journal_position: int
    checkpoint_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def valid(self) -> bool:
        return self.journal_position >= 0 and self.state.revision >= 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint",
            "version": "1.0",
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
            "journal_position": self.journal_position,
            "state": self.state.to_dict(),
            "valid": self.valid,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InteractionCheckpoint":
        raw_state = value.get("state")
        if not isinstance(raw_state, Mapping):
            raise ValueError("interaction checkpoint requires state")
        checkpoint = cls(
            checkpoint_id=str(value.get("checkpoint_id") or ""),
            created_at=str(value.get("created_at") or ""),
            journal_position=int(value.get("journal_position") or 0),
            state=InteractionSessionState.from_dict(raw_state),
        )
        if not checkpoint.valid:
            raise ValueError("interaction checkpoint is invalid")
        return checkpoint


@dataclass(frozen=True, slots=True)
class CheckpointRestoreResult:
    session: VisualizationInteractionSession
    checkpoint: InteractionCheckpoint
    replayed_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint-restore-result",
            "version": "1.0",
            "checkpoint": self.checkpoint.to_dict(),
            "state": self.session.state.to_dict(),
            "replayed_count": self.replayed_count,
            "renderer_neutral": True,
        }


class VisualizationInteractionCheckpointStore:
    """Create, retain and restore bounded interaction checkpoints."""

    def __init__(self, *, capacity: int = 16) -> None:
        if int(capacity) <= 0:
            raise ValueError("checkpoint capacity must be positive")
        self._capacity = int(capacity)
        self._checkpoints: list[InteractionCheckpoint] = []

    @property
    def checkpoints(self) -> tuple[InteractionCheckpoint, ...]:
        return tuple(self._checkpoints)

    @property
    def latest(self) -> InteractionCheckpoint | None:
        return self._checkpoints[-1] if self._checkpoints else None

    def create(
        self,
        session: VisualizationInteractionSession,
        journal: VisualizationInteractionJournal,
        *,
        checkpoint_id: str = "",
    ) -> InteractionCheckpoint:
        checkpoint = InteractionCheckpoint(
            state=session.state,
            journal_position=len(journal.entries),
            checkpoint_id=checkpoint_id,
        )
        self._checkpoints.append(checkpoint)
        overflow = len(self._checkpoints) - self._capacity
        if overflow > 0:
            del self._checkpoints[:overflow]
        return checkpoint

    def restore(
        self,
        checkpoint: InteractionCheckpoint | Mapping[str, Any] | None = None,
        *,
        history_limit: int = 100,
    ) -> CheckpointRestoreResult:
        resolved = checkpoint
        if resolved is None:
            resolved = self.latest
        elif not isinstance(resolved, InteractionCheckpoint):
            resolved = InteractionCheckpoint.from_dict(resolved)
        if resolved is None:
            raise ValueError("no interaction checkpoint available")
        session = VisualizationInteractionSession.from_state(
            resolved.state,
            history_limit=history_limit,
        )
        return CheckpointRestoreResult(session=session, checkpoint=resolved)

    def clear(self) -> None:
        self._checkpoints.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.checkpoint-store",
            "version": "1.0",
            "capacity": self._capacity,
            "checkpoints": [item.to_dict() for item in self._checkpoints],
            "checkpoint_count": len(self._checkpoints),
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VisualizationInteractionCheckpointStore":
        store = cls(capacity=int(value.get("capacity") or 16))
        raw = value.get("checkpoints") or ()
        store._checkpoints = [
            InteractionCheckpoint.from_dict(item)
            for item in raw
            if isinstance(item, Mapping)
        ]
        if len(store._checkpoints) > store._capacity:
            store._checkpoints = store._checkpoints[-store._capacity:]
        return store
