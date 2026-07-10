"""Serializable journal and replay support for visualization interactions.

The journal stores validated interaction events in deterministic sequence order.
It can replay them into a fresh interaction session, enabling workspace restore,
diagnostics and reproducible interaction tests without moving state logic to UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from services.visualization_interaction_events import (
    InteractionEventType,
    VisualizationInteractionEvent,
    VisualizationInteractionEventDispatcher,
)
from services.visualization_interaction_session import (
    InteractionSessionState,
    VisualizationInteractionSession,
)
from services.visualization_render_model import VisualizationRenderModel
from services.visualization_spatial_index import VisualizationSpatialIndex


ModelResolver = Callable[["InteractionJournalEntry"], VisualizationRenderModel | Mapping[str, Any] | None]


@dataclass(frozen=True, slots=True)
class InteractionJournalEntry:
    sequence: int
    event: VisualizationInteractionEvent
    before_revision: int
    after_revision: int

    @property
    def changed(self) -> bool:
        return self.after_revision != self.before_revision

    @property
    def valid(self) -> bool:
        return self.sequence >= 0 and self.before_revision >= 0 and self.after_revision >= 0 and self.event.valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.journal-entry",
            "version": "1.0",
            "sequence": self.sequence,
            "event": self.event.to_dict(),
            "before_revision": self.before_revision,
            "after_revision": self.after_revision,
            "changed": self.changed,
            "valid": self.valid,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InteractionJournalEntry":
        raw_event = value.get("event")
        if not isinstance(raw_event, Mapping):
            raise ValueError("journal entry requires event")
        return cls(
            sequence=int(value.get("sequence", -1)),
            event=VisualizationInteractionEvent.from_dict(raw_event),
            before_revision=int(value.get("before_revision", 0)),
            after_revision=int(value.get("after_revision", 0)),
        )


@dataclass(frozen=True, slots=True)
class InteractionReplayResult:
    state: InteractionSessionState
    applied_count: int
    changed_count: int
    skipped_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.replay-result",
            "version": "1.0",
            "state": self.state.to_dict(),
            "applied_count": self.applied_count,
            "changed_count": self.changed_count,
            "skipped_count": self.skipped_count,
            "renderer_neutral": True,
        }


@dataclass(slots=True)
class VisualizationInteractionJournal:
    """Append-only interaction event journal with deterministic replay."""

    entries: list[InteractionJournalEntry] = field(default_factory=list)
    dispatcher: VisualizationInteractionEventDispatcher = field(
        default_factory=VisualizationInteractionEventDispatcher,
        repr=False,
    )

    def dispatch_and_record(
        self,
        session: VisualizationInteractionSession,
        event: VisualizationInteractionEvent | Mapping[str, Any],
        *,
        model: VisualizationRenderModel | Mapping[str, Any] | None = None,
        spatial_index: VisualizationSpatialIndex | None = None,
    ) -> InteractionSessionState:
        resolved = event if isinstance(event, VisualizationInteractionEvent) else VisualizationInteractionEvent.from_dict(event)
        if not resolved.valid:
            raise ValueError("interaction event is invalid")
        before = session.state.revision
        state = self.dispatcher.dispatch(session, resolved, model=model, spatial_index=spatial_index)
        self.entries.append(
            InteractionJournalEntry(
                sequence=len(self.entries),
                event=resolved,
                before_revision=before,
                after_revision=state.revision,
            )
        )
        return state

    def replay(
        self,
        session: VisualizationInteractionSession,
        *,
        model: VisualizationRenderModel | Mapping[str, Any] | None = None,
        model_resolver: ModelResolver | None = None,
        spatial_index: VisualizationSpatialIndex | None = None,
        skip_cursor_without_model: bool = False,
    ) -> InteractionReplayResult:
        applied = 0
        changed = 0
        skipped = 0
        for entry in sorted(self.entries, key=lambda item: item.sequence):
            event_model = model_resolver(entry) if model_resolver is not None else model
            if entry.event.kind is InteractionEventType.CURSOR_UPDATE and event_model is None:
                if skip_cursor_without_model:
                    skipped += 1
                    continue
                raise ValueError("cursor replay requires render model")
            before = session.state.revision
            self.dispatcher.dispatch(session, entry.event, model=event_model, spatial_index=spatial_index)
            applied += 1
            if session.state.revision != before:
                changed += 1
        return InteractionReplayResult(session.state, applied, changed, skipped)

    def clear(self) -> None:
        self.entries.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.journal",
            "version": "1.0",
            "entries": [entry.to_dict() for entry in self.entries],
            "entry_count": len(self.entries),
            "changed_count": sum(1 for entry in self.entries if entry.changed),
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VisualizationInteractionJournal":
        raw_entries = value.get("entries") or ()
        entries = [
            InteractionJournalEntry.from_dict(item)
            for item in raw_entries
            if isinstance(item, Mapping)
        ]
        entries.sort(key=lambda item: item.sequence)
        expected = list(range(len(entries)))
        actual = [entry.sequence for entry in entries]
        if actual != expected:
            raise ValueError("journal sequence must be contiguous and start at zero")
        if not all(entry.valid for entry in entries):
            raise ValueError("journal contains invalid entries")
        return cls(entries=entries)
